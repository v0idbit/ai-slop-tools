"""Command-line interface."""

import argparse
import logging
import sys

from .http import fetch_doc_index
from .manifest import load_manifest
from .orchestrator import check_thresholds, remove_stale_files, run_fetch
from .urls import normalize_url

log = logging.getLogger("cc_docs_scraper")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and mirror Claude Code documentation "
        "as markdown.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Re-fetch and report changes without writing files.",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Fetch a single URL instead of the full index.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cached timestamps, thresholds, and re-download "
        "everything.",
    )
    args = parser.parse_args()

    manifest = load_manifest()

    if args.url:
        url = normalize_url(args.url)
        run_fetch(
            [url], manifest,
            verify_only=args.verify, force=args.force,
        )
        return

    # Phase 1: fetch the doc index, checking if it changed
    stored_index_lm = None if args.force else manifest.get(
        "index_last_modified"
    )
    index_urls, new_index_lm = fetch_doc_index(
        last_modified=stored_index_lm,
    )

    if index_urls is None:
        # Index unchanged — but individual pages may still have changed.
        # Rebuild URL list from manifest.
        index_urls = sorted(
            meta["url"]
            for meta in manifest.get("files", {}).values()
            if "url" in meta
        )
        if not index_urls:
            log.error("No doc URLs in index or manifest.")
            sys.exit(1)
        log.info(
            "Index unchanged; checking %d known pages for updates",
            len(index_urls),
        )
    else:
        if not index_urls:
            log.error("No doc URLs found in index.")
            sys.exit(1)

        # Threshold: catch massive URL count drops before touching files
        if not args.force:
            prev_count = len(manifest.get("files", {}))
            if prev_count > 0 and len(index_urls) < prev_count * 0.5:
                log.error(
                    "THRESHOLD: index returned %d URLs but manifest "
                    "has %d files (>50%% drop). Possible site migration "
                    "or index breakage. Aborting to protect local "
                    "mirror. Use --force to override.",
                    len(index_urls), prev_count,
                )
                sys.exit(2)

        # Phase 1b: detect removed pages
        removed = remove_stale_files(
            index_urls, manifest, verify_only=args.verify,
        )
        if removed:
            log.info("Removed %d stale file(s)", removed)

        # Store new index timestamp
        if new_index_lm and not args.verify:
            manifest["index_last_modified"] = new_index_lm

    # Phase 2: conditionally fetch each page
    stats = run_fetch(
        index_urls, manifest,
        verify_only=args.verify, force=args.force,
    )

    # Phase 3: post-fetch threshold check
    if not args.force and not check_thresholds(
        stats, manifest, len(index_urls),
    ):
        sys.exit(2)


if __name__ == "__main__":
    main()
