"""Fetch orchestration, stale file removal, and threshold checks."""

import logging
import random
import time
from pathlib import Path
from typing import Callable

from .constants import MANIFEST_FILE, OUTPUT_DIR
from .content import compute_hash
from .http import fetch_markdown
from .manifest import save_manifest
from .urls import url_to_filepath

log = logging.getLogger("cc_docs_scraper")

# Type alias for the fetch function signature
FetchFn = Callable[
    [str, str | None],
    tuple[str | None, str | None, bool],
]


def run_fetch(
    urls: list[str],
    manifest: dict,
    *,
    verify_only: bool = False,
    force: bool = False,
    fetch_fn: FetchFn = fetch_markdown,
    output_dir: Path = OUTPUT_DIR,
    manifest_file: Path = MANIFEST_FILE,
) -> dict[str, int]:
    """Fetch markdown for each URL, update files & manifest.

    Returns the stats dict with counts for each outcome.
    """
    files = manifest.setdefault("files", {})

    stats = {
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "not_modified": 0,
        "failed": 0,
    }

    for i, url in enumerate(urls, 1):
        filepath = url_to_filepath(url, output_dir=output_dir)
        rel_key = str(filepath)
        existing = files.get(rel_key, {})

        # Use stored Last-Modified for conditional request (skip on force)
        ims = None if force else existing.get("last_modified")

        log.info("[%d/%d] %s", i, len(urls), url)
        content, last_modified, not_modified = fetch_fn(
            url, ims,
        )

        if not_modified:
            stats["not_modified"] += 1
            log.debug("  not modified (304)")
            continue

        if content is None:
            stats["failed"] += 1
            continue

        content_hash = compute_hash(content)
        prev_hash = existing.get("sha256")

        if prev_hash == content_hash:
            # Content identical despite 200 — update last_modified timestamp
            stats["unchanged"] += 1
            if last_modified and not verify_only:
                existing["last_modified"] = last_modified
            log.debug("  unchanged (hash match)")
            continue

        if verify_only:
            status = "would update" if prev_hash else "would create"
            log.info("  %s  %s", status, filepath)
            stats["updated" if prev_hash else "new"] += 1
            continue

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, "utf-8")

        files[rel_key] = {
            "url": url,
            "sha256": content_hash,
            "last_modified": last_modified,
            "last_fetched": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
        }
        stats["updated" if prev_hash else "new"] += 1
        log.info("  wrote %s", filepath)

        # Rate-limit between requests (only on actual downloads)
        if i < len(urls):
            time.sleep(random.uniform(0.5, 1.0))

    if not verify_only:
        save_manifest(
            manifest,
            manifest_file=manifest_file,
            output_dir=output_dir,
        )

    log.info(
        "Done — new: %d, updated: %d, unchanged: %d, "
        "not_modified: %d, failed: %d",
        stats["new"], stats["updated"], stats["unchanged"],
        stats["not_modified"], stats["failed"],
    )

    return stats


def remove_stale_files(
    current_urls: list[str],
    manifest: dict,
    *,
    verify_only: bool = False,
    output_dir: Path = OUTPUT_DIR,
) -> int:
    """Delete local files whose URLs no longer appear in the index.

    Returns the number of files removed (or that would be removed in
    verify mode).
    """
    files = manifest.get("files", {})
    current_url_set = set(current_urls)

    stale_keys = [
        key for key, meta in files.items()
        if meta.get("url") not in current_url_set
    ]

    if not stale_keys:
        return 0

    for key in stale_keys:
        filepath = Path(key)
        if verify_only:
            log.info("  would delete %s (removed from index)", filepath)
        else:
            if filepath.exists():
                filepath.unlink()
                log.info("  deleted %s (removed from index)", filepath)
            del files[key]

    return len(stale_keys)


def check_thresholds(
    stats: dict[str, int],
    manifest: dict,
    index_url_count: int,
) -> bool:
    """Check for anomalies that suggest a docs site migration or breakage.

    Compares current results against the manifest's previous state.
    Returns True if everything looks normal, False if a problem was detected.
    """
    prev_file_count = len(manifest.get("files", {}))
    ok_count = (
        stats["new"] + stats["updated"]
        + stats["unchanged"] + stats["not_modified"]
    )

    # On the very first run there's nothing to compare against
    if prev_file_count == 0:
        return True

    # Index returned far fewer URLs than we previously tracked
    if index_url_count < prev_file_count * 0.5:
        log.error(
            "THRESHOLD: index returned %d URLs but manifest has %d files "
            "(>50%% drop). Possible site migration or index breakage. "
            "Aborting to protect local mirror. "
            "Use --force to override.",
            index_url_count, prev_file_count,
        )
        return False

    # Most pages failed to fetch
    total = ok_count + stats["failed"]
    if total > 0 and stats["failed"] > total * 0.5:
        log.error(
            "THRESHOLD: %d of %d pages failed to fetch (>50%%). "
            "Possible site migration or connectivity issue. "
            "Use --force to override.",
            stats["failed"], total,
        )
        return False

    return True
