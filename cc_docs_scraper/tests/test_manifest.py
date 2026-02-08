"""Tests for cc_docs_scraper.manifest."""

from cc_docs_scraper.manifest import load_manifest, save_manifest


class TestManifest:
    def test_missing_file_returns_empty_structure(self, tmp_path):
        manifest = load_manifest(tmp_path / "nonexistent.json")
        assert manifest == {"files": {}, "index_last_modified": None}

    def test_round_trip(self, tmp_path):
        manifest_file = tmp_path / "manifest.json"
        data = {
            "files": {
                "docs/overview.md": {
                    "url": "https://code.claude.com/docs/en/overview.md",
                    "sha256": "abc123",
                    "last_modified": "Wed, 01 Jan 2025 00:00:00 GMT",
                }
            },
            "index_last_modified": "Wed, 01 Jan 2025 00:00:00 GMT",
        }
        save_manifest(data, manifest_file=manifest_file, output_dir=tmp_path)
        loaded = load_manifest(manifest_file)
        assert loaded == data

    def test_creates_output_dir_if_absent(self, tmp_path):
        nested = tmp_path / "sub" / "dir"
        manifest_file = nested / "manifest.json"
        save_manifest(
            {"files": {}, "index_last_modified": None},
            manifest_file=manifest_file,
            output_dir=nested,
        )
        assert manifest_file.exists()

    def test_overwrites_existing_manifest(self, tmp_path):
        manifest_file = tmp_path / "manifest.json"
        save_manifest(
            {"files": {"a": 1}, "index_last_modified": None},
            manifest_file=manifest_file,
            output_dir=tmp_path,
        )
        save_manifest(
            {"files": {"b": 2}, "index_last_modified": None},
            manifest_file=manifest_file,
            output_dir=tmp_path,
        )
        loaded = load_manifest(manifest_file)
        assert "b" in loaded["files"]
        assert "a" not in loaded["files"]
