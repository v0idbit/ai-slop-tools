"""Tests for cc_docs_scraper.urls."""

import pytest

from cc_docs_scraper.urls import normalize_url, url_to_filepath, validate_url


# -- validate_url ----------------------------------------------------------

class TestValidateUrl:
    def test_accepts_code_claude_com(self):
        validate_url("https://code.claude.com/docs/en/overview.md")

    def test_accepts_docs_anthropic_com(self):
        validate_url("https://docs.anthropic.com/en/docs/claude-code/overview")

    def test_rejects_unknown_host(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_url("https://evil.com/docs/en/overview.md")

    def test_rejects_http_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("http://code.claude.com/docs/en/overview.md")

    def test_rejects_no_host(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_url("/docs/en/overview.md")


# -- normalize_url ---------------------------------------------------------

class TestNormalizeUrl:
    def test_already_canonical(self):
        url = "https://code.claude.com/docs/en/overview.md"
        assert normalize_url(url) == url

    def test_appends_md_extension(self):
        url = "https://code.claude.com/docs/en/overview"
        assert normalize_url(url) == "https://code.claude.com/docs/en/overview.md"

    def test_no_double_md(self):
        url = "https://code.claude.com/docs/en/overview.md"
        assert normalize_url(url).endswith("/overview.md")
        assert ".md.md" not in normalize_url(url)

    def test_legacy_url_with_relative_path(self):
        url = "https://docs.anthropic.com/en/docs/claude-code/hooks"
        assert normalize_url(url) == "https://code.claude.com/docs/en/hooks.md"

    def test_legacy_url_bare_claude_code(self):
        url = "https://docs.anthropic.com/en/docs/claude-code"
        assert normalize_url(url) == "https://code.claude.com/docs/en/overview.md"

    def test_strips_trailing_slash(self):
        url = "https://code.claude.com/docs/en/overview/"
        assert normalize_url(url) == "https://code.claude.com/docs/en/overview.md"


# -- url_to_filepath -------------------------------------------------------

class TestUrlToFilepath:
    def test_basic_mapping(self, output_dir):
        url = "https://code.claude.com/docs/en/hooks-guide.md"
        result = url_to_filepath(url, output_dir=output_dir)
        assert result == output_dir / "hooks-guide.md"

    def test_empty_relative_becomes_index(self, output_dir):
        url = "https://code.claude.com/docs/en/"
        result = url_to_filepath(url, output_dir=output_dir)
        assert result == output_dir / "index.md"

    def test_rejects_path_traversal(self, output_dir):
        url = "https://code.claude.com/docs/en/../../../etc/passwd"
        with pytest.raises(ValueError):
            url_to_filepath(url, output_dir=output_dir)

    def test_rejects_wrong_prefix(self, output_dir):
        url = "https://code.claude.com/other/path.md"
        with pytest.raises(ValueError, match="does not start with"):
            url_to_filepath(url, output_dir=output_dir)
