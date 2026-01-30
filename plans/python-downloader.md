# Plan: Python downloader for Finlex Open Data

## Goals
- Download Akoma Ntoso documents and related assets for:
  - act
  - judgment
  - doc
  - doc/authority-regulation
- Save data into a clear folder structure by document type, year, number, and language/version.

## Inputs
- OpenAPI spec: https://opendata.finlex.fi/Finlex_avoin_data_v0_4_0.yaml
- Findings: [docs/finlex-data-structure.md](../docs/finlex-data-structure.md)

## Proposed folder structure
```
<output_root>/
  act/
    <actDocumentType>/
      <year>/<number>/<langAndVersion>/
        main.xml
        main.pdf (optional)
        main.zip (optional ZIP from main.akn)
        media/<mediaFilename>
  judgment/
    <judgmentDocumentType>/
      <year>/<number>/<langAndVersion>/...
  doc/
    <docDocumentType>/
      <year>/<number>/<langAndVersion>/...
  doc/authority-regulation/
    <authority>/<year>/<number>/<langAndVersion>/...
```

## Steps

### Phase 1: Core infrastructure
- [x] 1. **Project setup**
   - [x] Create Python package structure (`src/finlex_downloader/`).
   - [x] Add `pyproject.toml` with dependencies (requests, pyyaml, lxml).
   - [x] Set up logging.

- [x] 2. **HTTP client module**
   - [x] Implement base client with User-Agent header.
   - [x] Add retry logic with exponential backoff for 429, 5xx, timeouts.
   - [x] Configurable sleep between requests.

- [x] 3. **Test & validate Phase 1**
   - [x] Unit test: retry logic triggers on 429/5xx.
   - [x] Unit test: User-Agent header is always sent.
   - [x] Manual test: fetch one document from API.

---

### Phase 2: Listing and URL handling
- [x] 4. **Spec-driven endpoint map**
   - [x] Parse OpenAPI YAML to list endpoints for act/judgment/doc and authority-regulation.
   - [x] Identify list endpoints and detail endpoints (XML, PDF, ZIP, media).

- [x] 5. **Listing strategy**
   - [x] Use list endpoints with paging (`page`, `limit`) and filters (e.g., year range, langAndVersion).
   - [x] Support per-type year settings (e.g., last N years for act, different N for judgment).
   - [x] Collect `akn_uri` values from JSON list responses.

- [x] 6. **URL/path utilities**
   - [x] Parse `akn_uri` to extract document type, year, number, langAndVersion.
   - [x] Build local folder path from URI components.

- [x] 7. **Test & validate Phase 2**
   - [x] Unit test: URL parsing extracts correct components.
   - [x] Unit test: folder path generation matches expected structure.
   - [x] Manual test: list endpoint returns valid JSON with `akn_uri`.

---

### Phase 3: Download strategy
- [x] 8. **Document downloader**
   - [x] For each `akn_uri`: Fetch XML (default Akoma Ntoso).
   - [x] Optionally fetch `main.pdf`.
   - [x] Optionally fetch ZIP (`main.akn` with `Accept: application/zip`).
   - [x] Skip existing files unless `--force` is set.

- [x] 9. **Media discovery**
   - [x] Parse Akoma Ntoso XML for media references in elements like `<img>`, `<ref>`, and `<attachment>`.
   - [x] Follow relative links (HATEOAS) to fetch media assets.

- [x] 10. **Test & validate Phase 3**
    - [x] Unit test: XML parsing finds media links in sample XML.
    - [x] Unit test: download skips existing files.
    - [x] Manual test: download one act with PDF and media.

---

### Phase 4: Persistence and state
- [x] 11. **Folder structure**
    - [x] Save using the folder structure defined above.

- [x] 12. **Resumability / checkpointing**
    - [x] Maintain a state file (e.g., `state.json`) tracking last completed page and URI.
    - [x] On restart, resume from last checkpoint instead of starting over.

- [x] 13. **Metadata logging**
    - [x] Write a manifest file (e.g., `manifest.json`) per download batch.
    - [x] Include: document URIs, timestamps, status (success/skipped/error), file paths.

- [x] 14. **Test & validate Phase 4**
    - [x] Unit test: state file saves and loads correctly.
    - [x] Unit test: manifest records success/error status.
    - [ ] Manual test: interrupt download, resume, verify no duplicates.

---

### Phase 5: CLI and error handling
- [x] 15. **Error handling**
    - [x] Retry with exponential backoff for HTTP 429, 5xx, and network timeouts.
    - [x] Log failures to manifest and continue with remaining items.

- [x] 16. **Concurrency**
    - [x] Single-threaded by default to respect rate limits.

- [x] 17. **CLI design**
    - [x] Arguments: `--output`, `--types`, `--years`, `--lang`, `--limit`, `--page`, `--sleep`, `--pdf`, `--zip`, `--media`, `--force`, `--dry-run`, `--resume`.
    - [x] Per-type year settings via `--years-act`, `--years-judgment`, `--years-doc`, `--years-authority-regulation`.
    - [x] Alternative: config file (YAML/JSON) for complex per-type settings.

- [x] 18. **Test & validate Phase 5**
    - [x] Unit test: CLI parses all arguments correctly.
    - [x] Unit test: dry-run mode logs actions without writing files.
    - [ ] Manual test: full end-to-end download of a small dataset.

---

### Phase 6: Documentation and release
- [ ] 19. **Deliverables**
    - [ ] Python script/module for downloading.
    - [ ] README section with usage examples and rate-limit guidance.
    - [ ] Example commands for common use cases.

- [ ] 20. **Final validation**
    - [ ] Run full test suite.
    - [ ] Download sample set of Finnish acts and verify folder structure.
    - [ ] Review manifest for completeness.
