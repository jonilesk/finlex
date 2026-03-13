# Copilot Instructions for finlex

## Build & Test

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run all tests (coverage enabled by default via pyproject.toml)
pytest

# Run a single test file
pytest tests/test_client.py

# Run a single test
pytest tests/test_client.py::test_user_agent_header_always_sent
```

There are no linters or formatters configured.

## Architecture

Two packages for downloading Finnish law from the Finlex Open Data API and converting it to Markdown.

### finlex_downloader — Download

```
cli.py          → Entry point, argument parsing, main download loop
  client.py     → HTTP client with retry/backoff and rate limiting
  listing.py    → Paginated document enumeration (generator-based)
  urls.py       → AKN URI parsing (regex) and filesystem path generation
  downloader.py → Multi-asset download (XML, PDF, ZIP, media)
  state.py      → Dual-file persistence: .state.json (resume) + manifest.json (audit)
```

`cli.py` orchestrates everything: it iterates categories → pages → documents, calling the other modules. There is no dependency injection; modules are imported directly.

**Dual persistence model:** `.state.json` tracks progress for resuming interrupted downloads (current category, page, completed URIs). `manifest.json` is an append-only audit log of every download attempt with status.

**URL parsing:** `urls.py` uses two regex patterns — authority-regulation documents have an extra `{authority}` segment in their URI, so the more specific pattern is tried first. `DocumentInfo.folder_path` maps URIs to the output directory structure.

**Pagination:** `list_documents()` is a generator that yields `ListItem` objects, stopping when a page returns fewer items than the limit, an error occurs, or `max_pages` is reached.

### finlex_converter — Convert XML to Markdown

```
cli.py          → Entry point: walks XML tree, converts to Markdown, builds index
  parser.py     → AKN XML → structured dataclasses (Statute/Chapter/Section/Subsection)
  renderer.py   → Structured data → Markdown with heading hierarchy
  citations.py  → Finnish citation parser (689/1997 → API path / folder path)
  indexer.py    → Builds JSON index mapping citation → file path + title
```

The converter reads downloaded XML, parses it with lxml (namespace-aware XPath), and writes one Markdown file per statute. After conversion it auto-generates `index.json` mapping every citation to its Markdown file path and metadata.

**Markdown format:** H1 = statute title, H2 = chapter (luku) or section (§) when no chapters, H3 = section within chapters. Metadata block with citation, ELI, dates, type.

## Key Conventions

- **HTTP mocking:** Tests use the `responses` library with `@responses.activate` decorator. Stack multiple `responses.add()` calls to simulate retries. Always set `sleep_seconds=0` on `FinlexClient` in tests.
- **Test fixtures:** No `conftest.py`. Tests use pytest's `tmp_path` builtin and inline XML strings (`.encode("utf-8")` for Finnish text). Test data samples live in `test-data/`.
- **State is saved immediately:** `StateManager.save()` is called after every state mutation to prevent data loss on interruption.
- **Completed URIs use a set** for O(1) lookup during resume.
- **Optional assets never fail the download:** Errors fetching PDF/ZIP/media are logged but don't mark the document as failed.
- **API client uses content negotiation:** Separate methods (`get_json`, `get_xml`, `get_pdf`, `get_zip`) set the appropriate Accept header.
- **All modules use a shared logger:** `logging.getLogger("finlex_downloader")` configured in `logging_config.py`.
