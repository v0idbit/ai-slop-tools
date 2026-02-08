"""Content hashing and markdown validation."""

import hashlib
import logging

log = logging.getLogger("cc_docs_scraper")


def compute_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_markdown(url: str, content: str) -> bool:
    """Return True if *content* looks like valid markdown."""
    if len(content.strip()) < 50:
        log.warning(
            "Content too short for %s (%d chars)", url, len(content)
        )
        return False

    if content.strip().startswith(("<!DOCTYPE", "<html")):
        log.warning("Response looks like HTML, not markdown: %s", url)
        return False

    md_indicators = ("#", "[", "```", "- ", "* ", "> ")
    if not any(indicator in content for indicator in md_indicators):
        log.warning("Response lacks markdown indicators: %s", url)
        return False

    return True
