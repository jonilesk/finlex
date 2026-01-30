# Finlex Open Data REST API — endpoint structure and how it’s defined (OpenAPI)

This document explains how the **Finlex Open Data** API endpoints are defined and how to use them at a practical level.

> Scope note: This covers the **official Finlex Open Data REST API** (Akoma Ntoso–based). The API surface is formally defined in an **OpenAPI description** and can be explored via **Swagger UI**. :contentReference[oaicite:0]{index=0}

---

## 1. Where the endpoint definitions live (OpenAPI / Swagger)

Finlex publishes an **OpenAPI (Swagger) interface description** that documents:
- endpoint paths
- supported HTTP methods
- response codes
- request/response formats
- parameter enums (e.g., `sortBy`)

You can browse it in the Finlex Open Data service using **Swagger UI**. :contentReference[oaicite:1]{index=1}

---

## 2. Base URL (server)

The Open Data REST API is served under:

- `https://opendata.finlex.fi/finlex/avoindata/v1` :contentReference[oaicite:2]{index=2}

> The docs also show some example links under `https://avoindata.finlex.fi/finlex/avoindata/v1/...` in sample responses. Treat the OpenAPI server definition + Swagger UI as the canonical reference for the supported servers. :contentReference[oaicite:3]{index=3}

---

## 3. Transport, auth, and operational requirements

### HTTPS / TLS
- HTTPS only; TLS 1.2+ required. :contentReference[oaicite:4]{index=4}

### Authentication
- No identification/registration is required for calling the Open Data API. :contentReference[oaicite:5]{index=5}

### Mandatory header
- All endpoints require a `User-Agent` header. :contentReference[oaicite:6]{index=6}

### Rate limiting
- The service may restrict call volumes; on restriction it returns **HTTP 429 Too Many Requests**. :contentReference[oaicite:7]{index=7}

### Compression
- Recommended: `Accept-Encoding: gzip` if your client supports it (helps with large documents). :contentReference[oaicite:8]{index=8}

---

## 4. Primary data model: Akoma Ntoso documents + “folder-like” paths

Finlex Open Data returns documents primarily as **Akoma Ntoso XML**. :contentReference[oaicite:9]{index=9}  
Endpoints generally map to Akoma Ntoso “document URIs” and related assets (PDF, media, attachments), using a path structure that resembles a folder hierarchy.

Key points:
- Primary representation: **Akoma Ntoso XML**. :contentReference[oaicite:10]{index=10}
- Some endpoints support **JSON** (typically listing/search results) depending on the endpoint and parameters. :contentReference[oaicite:11]{index=11}
- Documents may reference **PDF** for body text; some datasets may be PDF-only (served via XML metadata that points to PDF). :contentReference[oaicite:12]{index=12}

---

## 5. Common endpoint patterns (by example)

### 5.1 Retrieve a single statute (original version)
Example (Statute Book of Finland, statute number 123 of 2024, Finnish language/version marker `fin@`):

- `GET /akn/fi/act/statute/2024/123/fin%40` :contentReference[oaicite:13]{index=13}

Typical headers:
- `Accept: application/xml`
- `User-Agent: <something>`

### 5.2 List statutes (paged), optionally as JSON
Example list call with paging and filters:

- `GET /akn/fi/act/statute/list?format=json&page=1&limit=5&sortBy=dateIssued&startYear=2024&endYear=2024&LangAndVersion=fin%40&typeStatute=act&categoryStatute=new-statute` :contentReference[oaicite:14]{index=14}

This returns a list of items with `akn_uri` links you can then fetch individually. :contentReference[oaicite:15]{index=15}

### 5.3 Retrieve a PDF that contains body text
Example:

- `GET /akn/fi/doc/authority-regulation/metsahallitus/1996/32082/fin%40/main.pdf` :contentReference[oaicite:16]{index=16}

Use `Accept: application/pdf` + `User-Agent`.

### 5.4 Retrieve “zip package” for an Akoma Ntoso document (XML + assets)
Example (up-to-date consolidated act with images/appendices packaged as ZIP):

- `GET /akn/fi/act/statute-consolidated/2018/729/fin%40/main.akn` with `Accept: application/zip` :contentReference[oaicite:17]{index=17}

### 5.5 Retrieve an embedded media file (HATEOAS)
Media and attachments are typically referenced with **relative links** in the XML. The API supports following them per **HATEOAS**.

Example media retrieval:
- `GET /akn/fi/act/statute-consolidated/2018/729/fin%40/media/7296.gif` :contentReference[oaicite:18]{index=18}

---

## 6. Cross-cutting query parameters

### Paging (on list endpoints)
List/search endpoints use:
- `page` (first page is 1)
- `limit` (page size)

You iterate `page=1,2,3...` until the last page returns fewer items than `limit`. :contentReference[oaicite:19]{index=19}

> Note: Finlex has changed API limits over time (e.g., limit max reduced). Track “changes” notes and/or the current OpenAPI spec. :contentReference[oaicite:20]{index=20}

### Sorting
- `sortBy` exists on list endpoints; its allowed values are an enum defined in the OpenAPI description. :contentReference[oaicite:21]{index=21}

### Format negotiation
- Many document endpoints return XML; some list endpoints support `format=json`. :contentReference[oaicite:22]{index=22}

---

## 7. Datasets and categories (what you’ll see in Swagger)

Finlex Open Data is organized around major material categories, including:
- Legislation (updated legislation, statute book, translations, Sámi statutes)
- Case law
- Authorities
- Treaties
- Government proposals :contentReference[oaicite:23]{index=23}

For bulk acquisition, Finlex also offers downloadable ZIP packages per dataset via UI, updated daily. :contentReference[oaicite:24]{index=24}

---

## 8. Practical integration checklist (minimal)

1. Use the OpenAPI / Swagger UI to identify the exact endpoint + parameters you need. :contentReference[oaicite:25]{index=25}  
2. Always send a `User-Agent`. :contentReference[oaicite:26]{index=26}  
3. Prefer `Accept-Encoding: gzip` for large XML/PDF/ZIP downloads. :contentReference[oaicite:27]{index=27}  
4. Implement backoff for HTTP 429. :contentReference[oaicite:28]{index=28}  
5. For attachments/media/PDF referenced by XML, follow the relative links (HATEOAS). :contentReference[oaicite:29]{index=29}  

---

## 9. Next step: extract the full endpoint inventory

If you need an enumerated list of all endpoints (by tag/category), the authoritative source is the **Swagger/OpenAPI** description exposed in the Finlex Open Data service. :contentReference[oaicite:30]{index=30}

(If you tell me which material group you care about—e.g., statutes, government proposals, or a specific court—I can outline the typical endpoint families and the retrieval strategy for that group.)
