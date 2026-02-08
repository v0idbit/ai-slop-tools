"""HTTP fetching with retry logic."""

import logging
import random
import re
import time

import requests

from .constants import (
    INDEX_URL,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BASE_DELAY,
    USER_AGENT,
)
from .content import validate_markdown
from .urls import validate_url

log = logging.getLogger("cc_docs_scraper")


def request_with_retry(
    url: str,
    if_modified_since: str | None = None,
) -> requests.Response:
    """GET *url* with exponential back-off and jitter.

    When *if_modified_since* is provided, sends the ``If-Modified-Since``
    header.  A 304 response is returned directly (not raised as an error).
    """
    validate_url(url)
    headers = {"User-Agent": USER_AGENT}
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 304:
                return resp
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = (
                RETRY_BASE_DELAY * (2 ** attempt)
                + random.uniform(0, 0.5)
            )
            log.warning(
                "Attempt %d for %s failed (%s), retrying in %.1fs …",
                attempt + 1, url, exc, delay,
            )
            time.sleep(delay)

    raise RuntimeError("Exceeded max retries")  # pragma: no cover


def fetch_doc_index(
    last_modified: str | None = None,
) -> tuple[list[str] | None, str | None]:
    """Fetch llms.txt and return doc URLs and Last-Modified header.

    Uses ``If-Modified-Since`` when *last_modified* is provided.
    Returns ``(None, stored_last_modified)`` on 304 (no change to the
    URL list itself).
    """
    log.info("Fetching doc index from %s", INDEX_URL)
    resp = request_with_retry(INDEX_URL, if_modified_since=last_modified)

    if resp.status_code == 304:
        log.info("Doc index unchanged (304)")
        return None, last_modified

    urls: list[str] = []
    for match in re.finditer(
        r"\(https://code\.claude\.com/docs/en/[^)]+\.md\)", resp.text
    ):
        url = match.group(0)[1:-1]
        urls.append(url)

    new_last_modified = resp.headers.get("Last-Modified")
    log.info("Found %d doc URLs in index", len(urls))
    return sorted(urls), new_last_modified


def fetch_markdown(
    url: str,
    if_modified_since: str | None = None,
) -> tuple[str | None, str | None, bool]:
    """Fetch a markdown doc page with conditional request support.

    Returns ``(content, last_modified_header, was_not_modified)``.
    - 304 → ``(None, None, True)``
    - 200 with valid markdown → ``(content, last_modified, False)``
    - failure/invalid → ``(None, None, False)``
    """
    try:
        resp = request_with_retry(url, if_modified_since=if_modified_since)
    except requests.RequestException as exc:
        log.error("Failed to fetch %s: %s", url, exc)
        return None, None, False

    if resp.status_code == 304:
        return None, None, True

    content = resp.text
    if not validate_markdown(url, content):
        return None, None, False

    return content, resp.headers.get("Last-Modified"), False
