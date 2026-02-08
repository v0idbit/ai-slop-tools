"""Tests for cc_docs_scraper.content."""

from cc_docs_scraper.content import compute_hash, validate_markdown

URL = "https://code.claude.com/docs/en/example.md"


# -- compute_hash ----------------------------------------------------------

class TestComputeHash:
    def test_returns_sha256(self):
        result = compute_hash("hello world")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert compute_hash("test") == compute_hash("test")

    def test_different_content_different_hash(self):
        assert compute_hash("a") != compute_hash("b")


# -- validate_markdown -----------------------------------------------------

class TestValidateMarkdown:
    def test_accepts_valid_markdown(self):
        content = "# Title\n\nThis is a paragraph with enough content to pass the length check."
        assert validate_markdown(URL, content) is True

    def test_rejects_short_content(self):
        assert validate_markdown(URL, "# Hi") is False

    def test_rejects_html(self):
        content = "<!DOCTYPE html><html><body>Long enough content to pass length check</body></html>"
        assert validate_markdown(URL, content) is False

    def test_rejects_no_indicators(self):
        content = "This is plain text without any markdown indicators at all, just a long paragraph of words."
        assert validate_markdown(URL, content) is False

    def test_accepts_list_content(self):
        content = "- First item in the list\n- Second item in the list\n- Third item enough to pass"
        assert validate_markdown(URL, content) is True

    def test_accepts_code_block(self):
        content = "```python\nprint('hello world')\n```\nSome more text to make it long enough for the check."
        assert validate_markdown(URL, content) is True

    def test_accepts_blockquote(self):
        content = "> This is a blockquote with enough text to pass the minimum length validation check."
        assert validate_markdown(URL, content) is True
