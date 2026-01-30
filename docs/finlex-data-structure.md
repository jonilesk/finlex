# Finlex Open Data API: data structures and formats

This document summarizes the observed data formats and structures based on the OpenAPI description and sample responses.

## Sources
- OpenAPI/Swagger spec (YAML): https://opendata.finlex.fi/Finlex_avoin_data_v0_4_0.yaml
- Local plan: ../plans/api-data-structure-analysis.md

## Formats by endpoint type
- Akoma Ntoso XML: primary document representation for act/judgment/doc endpoints.
- JSON: list endpoints support JSON list results.
- PDF: endpoints with /main.pdf return PDF.
- ZIP: endpoints with /main.akn and Accept: application/zip return ZIP packages with XML + assets.

## List response structure (JSON)
Observed JSON list response is an array of objects:
- akn_uri: string (absolute URL to the document)
- status: enum [NEW, MODIFIED]

Example (single item):
- akn_uri: https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/2025/51/fin@
- status: NEW

Paging parameters in OpenAPI:
- page (default 1)
- limit (max 10 on most list endpoints; max 4 on small-list endpoints)

## Akoma Ntoso XML structure (document detail)
Observed top-level structure:
- akomaNtoso (namespace http://docs.oasis-open.org/legaldocml/ns/akn/3.0)
  - act (contains="originalVersion", name="main")
    - meta
      - identification
        - FRBRWork
        - FRBRExpression
        - FRBRManifestation

Key identifiers and metadata:
- FRBRthis, FRBRuri
- FRBRalias (ELI)
- FRBRdate (dateIssued, datePublished)

## Assets and packaging
- main.pdf: PDF for document body text when available.
- main.akn: can be requested as ZIP to include XML and assets.
- media/{mediaFilename}: media assets referenced from XML (HATEOAS-style relative links).

## Language and version markers
- langAndVersion format: {iso639-3}@{optionalTemporalVersion}
- Examples: fin@, swe@, fin@20230525

## Constraints from OpenAPI
- User-Agent header is required.
- Sorting enum: number, dateIssued, modified.
- Limit defaults: 5 (max 10) or 3 (max 4) depending on endpoint.
