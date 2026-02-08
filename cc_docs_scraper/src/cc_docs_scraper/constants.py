"""Configuration constants and logging setup."""

import logging
from pathlib import Path

BASE_URL = "https://code.claude.com"
INDEX_URL = f"{BASE_URL}/docs/llms.txt"
ALLOWED_HOSTS = {"code.claude.com", "docs.anthropic.com"}
DOC_PREFIX = "/docs/en/"
OUTPUT_DIR = Path("docs")
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
USER_AGENT = "claude-code-docs-scraper/1.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cc_docs_scraper")
