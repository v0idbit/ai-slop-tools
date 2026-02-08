"""Tests for cc_docs_scraper.orchestrator.check_thresholds."""

from cc_docs_scraper.orchestrator import check_thresholds


def _make_manifest(n_files: int) -> dict:
    """Create a manifest with *n_files* dummy entries."""
    return {
        "files": {
            f"docs/page{i}.md": {"url": f"https://code.claude.com/docs/en/page{i}.md"}
            for i in range(n_files)
        }
    }


class TestCheckThresholds:
    def test_first_run_always_passes(self):
        stats = {"new": 10, "updated": 0, "unchanged": 0, "not_modified": 0, "failed": 0}
        assert check_thresholds(stats, _make_manifest(0), index_url_count=10) is True

    def test_normal_operation_passes(self):
        stats = {"new": 0, "updated": 2, "unchanged": 8, "not_modified": 0, "failed": 0}
        assert check_thresholds(stats, _make_manifest(10), index_url_count=10) is True

    def test_url_count_drop_over_50_percent_fails(self):
        stats = {"new": 0, "updated": 0, "unchanged": 4, "not_modified": 0, "failed": 0}
        # Manifest has 10 files but index only returned 4 (<50%)
        assert check_thresholds(stats, _make_manifest(10), index_url_count=4) is False

    def test_fetch_failure_over_50_percent_fails(self):
        stats = {"new": 0, "updated": 0, "unchanged": 2, "not_modified": 0, "failed": 8}
        assert check_thresholds(stats, _make_manifest(10), index_url_count=10) is False

    def test_exactly_50_percent_url_drop_passes(self):
        # 5 out of 10 = exactly 50%, not < 50%, so it passes
        stats = {"new": 0, "updated": 0, "unchanged": 5, "not_modified": 0, "failed": 0}
        assert check_thresholds(stats, _make_manifest(10), index_url_count=5) is True

    def test_exactly_50_percent_failure_passes(self):
        # 5 failed out of 10 total = exactly 50%, not > 50%, so it passes
        stats = {"new": 0, "updated": 0, "unchanged": 5, "not_modified": 0, "failed": 5}
        assert check_thresholds(stats, _make_manifest(10), index_url_count=10) is True
