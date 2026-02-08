# Claude Code Documentation Scraper

Downloads and maintains a local mirror of the Claude Code docs from `code.claude.com` as markdown files. Designed for environments with restricted or audited web access (e.g., HIPAA-compliant networks) where browsing the docs site directly is not feasible.

## Quick Start

```bash
uv sync
uv run cc-docs-scraper
```

## Usage

### Fetch all docs

```bash
uv run cc-docs-scraper
```

Discovers all Claude Code doc pages via `llms.txt`, saves markdown files under `docs/`, and writes `docs/manifest.json` with SHA-256 hashes and `Last-Modified` timestamps.

On subsequent runs, uses HTTP conditional requests (`If-Modified-Since`) to skip unchanged pages — only modified content is downloaded.

### Verify (dry run)

```bash
uv run cc-docs-scraper --verify
```

Re-fetches all pages and reports which files have changed, without writing anything to disk.

### Fetch a single URL

```bash
# New-style URL
uv run cc-docs-scraper --url https://code.claude.com/docs/en/overview.md

# Legacy URL (auto-converted)
uv run cc-docs-scraper --url https://docs.anthropic.com/en/docs/claude-code/overview
```

Useful for testing or updating a single page. Legacy `docs.anthropic.com` URLs are automatically translated to the current `code.claude.com` format.

### Force re-download

```bash
uv run cc-docs-scraper --force
```

Ignores cached `Last-Modified` timestamps and re-downloads everything.

### Cron usage

```cron
# Check for doc updates daily at 3am
0 3 * * * cd /path/to/cc_docs_scraper && uv run cc-docs-scraper >> /var/log/cc-docs-scraper.log 2>&1
```

A typical cron run against an unchanged site completes in ~12 seconds with zero content downloaded (55 lightweight 304 responses).

## Development

```bash
uv sync --dev
uv run pytest -v
```

## Output Structure

```
docs/
├── manifest.json
├── overview.md
├── setup.md
├── hooks.md
├── hooks-guide.md
├── permissions.md
└── …
```

`manifest.json` tracks each file's source URL, SHA-256 hash, `Last-Modified` header, and last-fetched timestamp. Pages removed from the index are automatically deleted on the next run.

## Dependencies

| Package | Version | Why |
|---------|---------|-----|
| `requests` | >=2.32 | HTTP client for fetching doc index and pages |

No other dependencies. Standard library only beyond `requests`.

## Security Audit Checklist

- [x] **URL validation** — only `https://code.claude.com` and `https://docs.anthropic.com` hosts are allowed; scheme is checked
- [x] **Path traversal prevention** — output paths are validated and resolved against the output directory
- [x] **No shell execution** — no `subprocess`, `os.system`, or `eval` calls
- [x] **No dynamic code** — no `exec`, `importlib`, or code generation
- [x] **File writes scoped** — all writes go under `./docs/`; resolved paths are checked with `is_relative_to()`
- [x] **Rate limiting** — random 0.5–1.0 s delay between requests
- [x] **Retry safety** — exponential backoff with jitter, max 3 attempts
- [x] **Content validation** — responses are checked for minimum length and markdown indicators; HTML responses are rejected
- [x] **Minimal dependencies** — only `requests`; everything else is stdlib
