# Finlex Open Data API — Consolidated Statutes Discovery

**Date:** 2026-03-14
**Base URL:** `https://opendata.finlex.fi/finlex/avoindata/v1`
**OpenAPI spec:** `https://opendata.finlex.fi/v3/api-docs` (OpenAPI 3.1.0)
**Required header:** `User-Agent: <any non-empty string>`

## Overview

The Finlex Open Data API serves Finnish legal documents in [Akoma Ntoso](http://www.akomantoso.org/) XML format. Three top-level document categories exist:

| Category   | Path prefix                      | Description                      |
|------------|----------------------------------|----------------------------------|
| **act**    | `/akn/fi/act/{actDocumentType}`  | Statutes (säädökset)             |
| **doc**    | `/akn/fi/doc/{docDocumentType}`  | Documents (e.g., authority regs) |
| **judgment** | `/akn/fi/judgment/{type}`      | Court decisions (päätökset)      |

For consolidated statutes, the `actDocumentType` is **`statute-consolidated`**.

---

## 1. List Endpoint

```
GET /akn/fi/act/statute-consolidated/list
```

### Query Parameters

| Parameter        | Type      | Default | Description |
|------------------|-----------|---------|-------------|
| `format`         | string    | `json`  | Response format: `json` or omit for JSON (default is JSON regardless) |
| `page`           | int       | 1       | Page number (min: 1) |
| `limit`          | int       | 5       | Page size (min: 1, **max: 10**) |
| `sortBy`         | string    | —       | Sort field: `number`, `dateIssued`, or `modified` |
| `startYear`      | int       | —       | Filter: earliest document year |
| `endYear`        | int       | —       | Filter: latest document year |
| `langAndVersion` | string    | —       | Language+version filter, e.g. `fin@` (Finnish, current), `swe@` (Swedish) |
| `publishedSince` | datetime  | —       | ISO 8601 datetime; returns items modified/published after this date |
| `dateIssued`     | date      | —       | Exact issue date filter |
| `keyword`        | string[]  | —       | Keyword filter (Finnish or Swedish terms) |
| `titleContains`  | string    | —       | Title substring search |
| `typeStatute`    | string    | —       | Statute type filter |
| `categoryStatute`| string    | —       | Statute category filter |
| `documentNumber` | string    | —       | Exact document number filter |

> **Note:** `LangAndVersion` in the URL query is case-insensitive on the parameter name, but the API spec uses `langAndVersion` (camelCase). Both work in practice.

### JSON Response Format

The response is a **flat JSON array** (no envelope, no total count, no pagination metadata):

```json
[
    {
        "akn_uri": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute-consolidated/2025/51/fin@",
        "status": "MODIFIED"
    },
    {
        "akn_uri": "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute-consolidated/2025/50/fin@",
        "status": "MODIFIED"
    }
]
```

**Fields:**
- `akn_uri` (string, URI) — Full URL of the document. Contains the year, number, language, and optional temporal version.
- `status` (string, enum) — Either `"NEW"` or `"MODIFIED"`. Only meaningful when used with `publishedSince`.

### Pagination Behavior

- **No total count** is returned in the response or headers.
- **Stopping condition:** When a page returns fewer items than `limit`, there are no more pages. An empty array `[]` means past the end.
- **Default sort order:** Descending by year/number (newest first). With `sortBy=dateIssued`, oldest first.
- **Maximum page size is 10.** Requesting `limit > 10` silently caps at 10.

### Dataset Size (as of 2026-03-14)

| Scope | Count |
|-------|-------|
| All items (all languages + temporal versions) | **~131,045** |
| Finnish only (`langAndVersion=fin@`) | **~42,479** |
| Year range | **1734–2025** |

> Items include both `fin@` and `swe@` (Finnish/Swedish) versions, plus temporal versions (e.g., `fin@20180817`).

---

## 2. Single Document Endpoint

```
GET /akn/fi/act/statute-consolidated/{year}/{number}/{langAndVersion}
```

### Important: Temporal Version Required

The bare `fin@` suffix (no temporal version) returns **404** for many documents. The list endpoint provides the correct temporal version suffix.

**Example:** Constitution of Finland (731/1999)
- ❌ `/1999/731/fin@` → 404
- ✅ `/1999/731/fin@20180817` → 200 (AKN XML)

The list endpoint shows: `akn_uri: .../1999/731/fin@20180817`

Some newer statutes **do** work with bare `fin@`:
- ✅ `/2025/51/fin@` → 200

### Response

Returns Akoma Ntoso XML (`Content-Type: application/xml`).

### Related Endpoints

| Endpoint | Description |
|----------|-------------|
| `/{year}/{number}` | All language/temporal versions (paginated, max 4) |
| `/{year}/{number}/{langAndVersion}/main.pdf` | PDF rendering |
| `/{year}/{number}/{langAndVersion}/main.akn` | ZIP package (XML + PDF + media) |
| `/{year}/{number}/{langAndVersion}/media/{filename}` | Attached media files |
| `/{year}/{number}/{langAndVersion}/corrigenda/{filename}` | Corrigenda (corrections) |

---

## 3. AKN XML Structure (Consolidated Statute)

Namespace: `http://docs.oasis-open.org/legaldocml/ns/akn/3.0`
Finlex namespace: `http://data.finlex.fi/schema/finlex`

### Top-Level Structure

```xml
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
            xmlns:finlex="http://data.finlex.fi/schema/finlex">
  <act contains="multipleVersions" name="main">
    <meta>...</meta>
    <preface>...</preface>
    <preamble>...</preamble>
    <body>...</body>
  </act>
</akomaNtoso>
```

### Meta Section

```xml
<meta>
  <identification source="#organization_fi.finlex">
    <FRBRWork>
      <FRBRthis value="/akn/fi/act/statute-consolidated/1999/731/!main"/>
      <FRBRuri value="/akn/fi/act/statute-consolidated/1999/731"/>
      <FRBRalias name="eli" value="http://data.finlex.fi/eli/sd/1999/731/ajantasa"/>
      <FRBRdate date="1999-06-11" name="dateIssued"/>
      <FRBRdate date="1999-06-17" name="datePublished"/>
      <FRBRsubtype value="statute-consolidated"/>
      <FRBRnumber value="731"/>
    </FRBRWork>
    <FRBRExpression>
      <FRBRuri value="/akn/fi/act/statute-consolidated/1999/731/fin@20180817"/>
      <FRBRalias name="eli" value="http://data.finlex.fi/eli/sd/1999/731/ajantasa/2018-10-05/fin"/>
      <FRBRdate date="2018-10-05" name="dateConsolidated"/>
      <FRBRversionNumber value="20180817"/>
      <FRBRlanguage language="fin"/>
    </FRBRExpression>
  </identification>
  <classification>
    <keyword showAs="Perustuslaki" value="..."/>
    <keyword showAs="Suomen perustuslaki" value="..."/>
  </classification>
  <proprietary>
    <finlex:documentYear>1999</finlex:documentYear>
    <finlex:typeStatute refersTo="#act"/>
    <finlex:isInForce value="true"/>
    <finlex:inForce>
      <finlex:dateEntryIntoForce date="2000-03-01"/>
    </finlex:inForce>
    <finlex:amendedBy>
      <finlex:statuteReference>
        <finlex:ref href="/akn/fi/act/statute/2018/817">817/2018</finlex:ref>
      </finlex:statuteReference>
    </finlex:amendedBy>
    <finlex:repeals>...</finlex:repeals>
    <finlex:issuedUnderThisAct>...</finlex:issuedUnderThisAct>
  </proprietary>
</meta>
```

**Key metadata fields:**
- `FRBRWork/FRBRnumber` — Statute number (e.g., 731)
- `FRBRWork/FRBRdate[@name='dateIssued']` — Date issued
- `FRBRExpression/FRBRdate[@name='dateConsolidated']` — Consolidation date
- `FRBRExpression/FRBRversionNumber` — Temporal version identifier
- `FRBRExpression/FRBRlanguage` — Language code (fin/swe)
- `FRBRalias[@name='eli']` — ELI (European Legislation Identifier) URI
- `finlex:isInForce` — Whether the statute is currently in force
- `finlex:amendedBy` — List of amending statutes with references
- `finlex:repeals` — Statutes repealed by this one
- `classification/keyword` — Finnish keywords

### Preface

```xml
<preface>
  <p>
    <docNumber>731/1999</docNumber>
    <docTitle>Suomen perustuslaki</docTitle>
  </p>
</preface>
```

### Body — Document Hierarchy

```
body
└── hcontainer[@name='statuteProvisionsWrapper']
    └── chapter (luku)
        ├── num ("1 luku")
        ├── heading ("Valtiojärjestyksen perusteet")
        └── section (§)
            ├── num ("1 §")
            ├── heading ("Valtiosääntö")
            └── subsection
                └── content
                    └── p (paragraph text)
```

**Element ID pattern (eId):**
- Chapter: `chp_1`
- Section: `chp_1__sec_1`
- Subsection: `chp_1__sec_1__subsec_1`
- Amended subsections include version suffix: `chp_1__sec_1__subsec_3v20111112`

### Example: Constitution of Finland (731/1999)

| Metric | Count |
|--------|-------|
| Chapters (luku) | 13 |
| Sections (§) | 131 |
| Subsections | 305 |

---

## 4. URI/Citation Mapping

Finnish statute citations use format **number/year** (e.g., `731/1999`).
API paths use **year/number** (reversed): `/1999/731/`.

Some old statutes use a compound number format: `1-000` (for the first statute of 1734), `4-000`, `5-000`.

### URI Structure

```
/akn/fi/act/statute-consolidated/{year}/{number}/{lang}@{temporalVersion}
```

- `{year}` — Year of the statute (e.g., 1999)
- `{number}` — Statute number (e.g., 731, or 4-000 for old compound numbers)
- `{lang}` — ISO 639-3 language code: `fin` (Finnish) or `swe` (Swedish)
- `{temporalVersion}` — Optional; when present, it's a concatenation of year + statute number of the amending act (e.g., `20180817` = statute 817/2018)

---

## 5. Additional Act Document Types

The `actDocumentType` path parameter is not limited to `statute-consolidated`. The API spec defines it as a generic string. Known values (from existing code):

- `statute-consolidated` — Consolidated (ajantasa) statutes
- `statute` — Original statutes (as published)
- `treaty-consolidated` — Consolidated treaties

---

## 6. Other Observations

1. **No authentication required** — only the `User-Agent` header is mandatory.
2. **Rate limiting** — Not documented in the OpenAPI spec but recommended to add delays between requests.
3. **Default sort order** — Without `sortBy`, results are returned in reverse chronological order (newest first).
4. **`sortBy=dateIssued`** — Returns oldest first (ascending by issue date).
5. **`sortBy=modified`** — Returns by modification/publication date; useful for change detection.
6. **`sortBy=number`** — Returns by document number within the year; affected by pagination across years.
7. **`keyword` param** — Accepts Finnish/Swedish keywords but returned empty results in testing; may need exact keyword ontology values.
8. **`titleContains`** — Substring search on statute title. Returned results for "perustuslaki" (Constitution).
9. **`publishedSince`** — Combined with `status` field in response, enables change detection/incremental sync.
10. **`format` parameter** — Default format is JSON. The list endpoint always returns JSON regardless of `format` value in testing.
11. **Empty response = 200** — The API returns HTTP 200 with `[]` when no results found, not 404.
12. **Content-Length present** — Response headers include `Content-Length`, allowing size estimation.

---

## 7. Downloading Only Effective (In-Force) Statutes

### What `langAndVersion=fin@` gives you

When filtering the list with `langAndVersion=fin@`, the API returns **only the latest Finnish version** of each statute — no older temporal versions, no Swedish translations. This yields ~42,479 items.

### In-force vs. repealed

The `fin@` filter does **not** exclude repealed statutes. Approximately 40% of consolidated statutes have `<finlex:isInForce value="false"/>`. There is **no API-level query parameter** to filter by in-force status.

### Strategy for "only effective law"

1. **List** with `langAndVersion=fin@` — gets one entry per statute (latest version)
2. **Download** the XML for each
3. **Check** `<finlex:isInForce value="true"/>` in the XML metadata
4. **Keep or skip** based on the in-force check

This check can be done either:
- **Post-download:** Download all, then filter (simpler, but downloads ~40% unnecessary data)
- **Inline:** Download XML, check `isInForce`, skip saving if `false` (saves disk space)

### Existing downloader compatibility

The existing `finlex-downloader` CLI **already supports** consolidated statutes:

```bash
finlex-downloader --types act --lang fin@ --years 300
```

This downloads all act types including `statute-consolidated`. But it has **no `isInForce` filter**. Adding one would require a code change to check the XML after download and skip/delete repealed statutes.
