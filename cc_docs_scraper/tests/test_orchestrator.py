"""Tests for cc_docs_scraper.orchestrator (run_fetch, remove_stale_files)."""

import pytest

from cc_docs_scraper.orchestrator import remove_stale_files, run_fetch

URL_A = "https://code.claude.com/docs/en/page-a.md"
URL_B = "https://code.claude.com/docs/en/page-b.md"

VALID_CONTENT = "# Title\n\nThis is a paragraph with enough content to pass the minimum length validation check."
UPDATED_CONTENT = "# Updated Title\n\nThis paragraph has different content that will produce a different SHA-256 hash value."
LAST_MODIFIED = "Wed, 01 Jan 2025 00:00:00 GMT"


def _fake_fetch(content=VALID_CONTENT, last_modified=LAST_MODIFIED, not_modified=False):
    """Return a fetch function that returns fixed values."""
    def fetch_fn(url, if_modified_since=None):
        return content, last_modified, not_modified
    return fetch_fn


def _fake_fetch_failure(url, if_modified_since=None):
    """Fetch function that simulates a failure."""
    return None, None, False


# -- run_fetch --------------------------------------------------------------

class TestRunFetch:
    def test_new_file_written(self, output_dir):
        manifest = {"files": {}}
        stats = run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["new"] == 1
        filepath = output_dir / "page-a.md"
        assert filepath.exists()
        assert filepath.read_text() == VALID_CONTENT

    def test_updated_file_overwritten(self, output_dir):
        filepath = output_dir / "page-a.md"
        filepath.write_text("old content", "utf-8")

        manifest = {
            "files": {
                str(filepath): {
                    "url": URL_A,
                    "sha256": "oldhash",
                    "last_modified": LAST_MODIFIED,
                }
            }
        }
        stats = run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["updated"] == 1
        assert filepath.read_text() == VALID_CONTENT

    def test_unchanged_file_skipped(self, output_dir):
        from cc_docs_scraper.content import compute_hash

        filepath = output_dir / "page-a.md"
        filepath.write_text(VALID_CONTENT, "utf-8")

        manifest = {
            "files": {
                str(filepath): {
                    "url": URL_A,
                    "sha256": compute_hash(VALID_CONTENT),
                    "last_modified": LAST_MODIFIED,
                }
            }
        }
        stats = run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["unchanged"] == 1
        assert stats["new"] == 0
        assert stats["updated"] == 0

    def test_304_counted(self, output_dir):
        manifest = {"files": {}}
        stats = run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch(content=None, last_modified=None, not_modified=True),
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["not_modified"] == 1

    def test_failure_counted(self, output_dir):
        manifest = {"files": {}}
        stats = run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch_failure,
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["failed"] == 1

    def test_verify_mode_does_not_write(self, output_dir):
        manifest = {"files": {}}
        stats = run_fetch(
            [URL_A], manifest,
            verify_only=True,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert stats["new"] == 1
        filepath = output_dir / "page-a.md"
        assert not filepath.exists()

    def test_force_mode_does_not_send_if_modified_since(self, output_dir):
        received_ims = []

        def tracking_fetch(url, if_modified_since=None):
            received_ims.append(if_modified_since)
            return VALID_CONTENT, LAST_MODIFIED, False

        filepath = output_dir / "page-a.md"
        manifest = {
            "files": {
                str(filepath): {
                    "url": URL_A,
                    "sha256": "oldhash",
                    "last_modified": LAST_MODIFIED,
                }
            }
        }
        run_fetch(
            [URL_A], manifest,
            force=True,
            fetch_fn=tracking_fetch,
            output_dir=output_dir,
            manifest_file=output_dir / "manifest.json",
        )
        assert received_ims == [None]

    def test_manifest_saved_after_fetch(self, output_dir):
        manifest_file = output_dir / "manifest.json"
        manifest = {"files": {}}
        run_fetch(
            [URL_A], manifest,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=manifest_file,
        )
        assert manifest_file.exists()

    def test_manifest_not_saved_in_verify_mode(self, output_dir):
        manifest_file = output_dir / "manifest.json"
        manifest = {"files": {}}
        run_fetch(
            [URL_A], manifest,
            verify_only=True,
            fetch_fn=_fake_fetch(),
            output_dir=output_dir,
            manifest_file=manifest_file,
        )
        assert not manifest_file.exists()


# -- remove_stale_files -----------------------------------------------------

class TestRemoveStaleFiles:
    def test_deletes_stale_file(self, output_dir):
        filepath = output_dir / "old-page.md"
        filepath.write_text("stale", "utf-8")

        manifest = {
            "files": {
                str(filepath): {
                    "url": "https://code.claude.com/docs/en/old-page.md",
                }
            }
        }
        removed = remove_stale_files(
            [URL_A], manifest, output_dir=output_dir,
        )
        assert removed == 1
        assert not filepath.exists()

    def test_verify_mode_does_not_delete(self, output_dir):
        filepath = output_dir / "old-page.md"
        filepath.write_text("stale", "utf-8")

        manifest = {
            "files": {
                str(filepath): {
                    "url": "https://code.claude.com/docs/en/old-page.md",
                }
            }
        }
        removed = remove_stale_files(
            [URL_A], manifest, verify_only=True, output_dir=output_dir,
        )
        assert removed == 1
        assert filepath.exists()  # not actually deleted

    def test_no_stale_returns_zero(self, output_dir):
        manifest = {
            "files": {
                str(output_dir / "page-a.md"): {"url": URL_A},
            }
        }
        removed = remove_stale_files(
            [URL_A], manifest, output_dir=output_dir,
        )
        assert removed == 0
