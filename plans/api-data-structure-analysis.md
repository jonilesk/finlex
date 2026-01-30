# Plan: Analyze Finlex Open Data API structure

## Goals
- Map the API surface (endpoints, parameters, formats) from the OpenAPI/Swagger definition.
- Identify core data shapes: list responses, document XML (Akoma Ntoso), media/PDF/ZIP assets.
- Produce a concise schema summary and retrieval workflow per material group (e.g., legislation, case law).

## Inputs
- OpenAPI/Swagger definition exposed by Finlex Open Data service.
- Example calls in docs: [docs/finlex-api.md](../docs/finlex-api.md).

## Steps
1. **Inventory endpoints**
   - Fetch the OpenAPI document from the Swagger UI endpoint.
   - Parse paths, methods, tags, parameters, and response schemas.
   - Group endpoints by tag/material category.

2. **Characterize response formats**
   - For each endpoint, note media types (XML/JSON/PDF/ZIP) and required headers.
   - Record which endpoints accept `format=json` and list query parameters (paging, sorting, filters).

3. **Sample representative responses**
   - Select one endpoint per category (e.g., statute list + statute detail).
   - Capture response structure:
     - JSON list shape (fields like `items`, `akn_uri`, paging fields).
     - Akoma Ntoso XML structure and key sections.
     - Attachment/media link patterns (HATEOAS relative URLs).
   - Download a small set of Finnish law document assets (e.g., `fin@` XML/PDF/ZIP) to confirm formats.

4. **Define canonical data model**
   - Map list response items to document retrieval flow (list → detail → assets).
   - Extract common identifiers (Akoma Ntoso URI parts).
   - Note versioning/language markers (e.g., `fin@`) and their placement.

5. **Summarize operational constraints**
   - Required headers (`User-Agent`, optional `Accept-Encoding: gzip`).
   - Rate limit handling (HTTP 429 backoff).

6. **Deliverables**
   - Endpoint catalog by tag.
   - Data structure summary (JSON list schema, XML sections, asset linkage).
   - Recommended retrieval workflow for each material group.

## Outputs
- A short report in `plans/` with endpoint inventory + data model notes.
- A findings document in `docs/` (e.g., `docs/finlex-data-structure.md`).
- Optional: a machine-readable extract of endpoint metadata (JSON/YAML) for downstream tooling.
