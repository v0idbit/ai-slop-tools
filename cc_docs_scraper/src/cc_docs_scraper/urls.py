"""URL validation, normalization, and filepath mapping."""

from pathlib import Path
from urllib.parse import urlparse

from .constants import ALLOWED_HOSTS, DOC_PREFIX, OUTPUT_DIR


def validate_url(url: str) -> None:
    """Ensure *url* points to an allowed host over HTTPS."""
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(
            f"URL host '{parsed.hostname}' is not allowed "
            f"(expected one of {ALLOWED_HOSTS})"
        )
    if parsed.scheme != "https":
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed (expected https)"
        )


def normalize_url(url: str) -> str:
    """Normalize a doc URL to the canonical code.claude.com form.

    Accepts both ``code.claude.com`` and legacy ``docs.anthropic.com``
    URLs and returns the canonical ``code.claude.com`` markdown URL.
    """
    parsed = urlparse(url)

    # Handle legacy docs.anthropic.com URLs
    if parsed.hostname == "docs.anthropic.com":
        path = parsed.path.rstrip("/")
        legacy_prefix = "/en/docs/claude-code/"
        if path.startswith(legacy_prefix):
            relative = path[len(legacy_prefix):]
            path = f"/docs/en/{relative}"
        elif path.startswith("/en/docs/claude-code"):
            path = "/docs/en/overview"
        url = f"https://code.claude.com{path}"
        parsed = urlparse(url)

    path = parsed.path.rstrip("/")
    if not path.endswith(".md"):
        path += ".md"

    return f"https://code.claude.com{path}"


def url_to_filepath(url: str, output_dir: Path = OUTPUT_DIR) -> Path:
    """Map a doc URL to a local file path under *output_dir*.

    Strips the ``/docs/en/`` prefix.  The URL already ends in ``.md``.
    Example: ``/docs/en/hooks-guide.md`` → ``docs/hooks-guide.md``
    """
    parsed = urlparse(url)
    path = parsed.path

    if not path.startswith(DOC_PREFIX):
        raise ValueError(
            f"URL path does not start with {DOC_PREFIX}: {path}"
        )

    relative = path[len(DOC_PREFIX):]

    if not relative:
        relative = "index.md"

    if not relative.endswith(".md"):
        relative += ".md"

    # Prevent path traversal
    parts = Path(relative).parts
    if any(part in (".", "..") or part.startswith("/") for part in parts):
        raise ValueError(f"Suspicious path components in URL: {path}")

    filepath = output_dir / relative

    if not filepath.resolve().is_relative_to(output_dir.resolve()):
        raise ValueError(
            f"Resolved path escapes output directory: {filepath}"
        )

    return filepath
