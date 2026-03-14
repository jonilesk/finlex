# Business Flows

How the two CLI tools work end-to-end.

## 1. Download Flow (`finlex-downloader`)

```
                                     Finlex Open Data API
                                     ────────────────────
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐    ┌───────────┐
│ CLI args │───▶│ Category │───▶│ Paginate │───▶│  Download  │───▶│   Save    │
│ parsing  │    │   loop   │    │  listing │    │  document  │    │  to disk  │
└─────────┘    └──────────┘    └──────────┘    └────────────┘    └───────────┘
                    │                │                │                 │
                    ▼                ▼                ▼                 ▼
              .state.json       API /list        API /{doc}       manifest.json
              (resume)         (JSON array)     (AKN XML)        (audit log)
```

### Step-by-step

**1. Parse arguments and initialize**

The CLI parses `--types`, `--subtypes`, `--lang`, `--years`, etc. Three managers are
created:
- `FinlexClient` — HTTP session with retry/backoff and rate limiting
- `StateManager` — Reads/writes `.state.json` for resume support
- `ManifestManager` — Reads/writes `manifest.json` as an audit log

**2. Iterate categories → subtypes**

For each `--types` value (e.g., `act`), the downloader resolves the list of document
subtypes to process:

| Category | Default subtypes |
|----------|-----------------|
| act | statute, statute-consolidated, statute-translated, statute-aland, statute-sami |
| judgment | kko, kho |
| doc | government-proposal, treaty, treaty-consolidated, authority-regulation |

If `--subtypes` is set, only matching subtypes are kept. For example,
`--types act --subtypes statute-consolidated` processes only consolidated statutes.

**3. Paginate the list endpoint**

For each subtype, `list_documents()` calls the API list endpoint:

```
GET /akn/fi/act/statute-consolidated/list
    ?format=json&page=1&limit=10&langAndVersion=fin@
    &startYear=1726&endYear=2025
```

The API returns a flat JSON array of `{akn_uri, status}` objects. The generator
yields one `ListItem` per document and advances to the next page until:
- A page returns fewer items than `limit` (last page)
- An empty response is received
- `--max-pages` is reached
- An HTTP error occurs

There is no total count in the API response — the end is detected by a short page.

**4. Download each document**

For each `ListItem`, `download_document()` runs this sequence:

```
Parse akn_uri → DocumentInfo (year, number, lang, folder path)
    │
    ├── File already exists and not --force?  →  status: "skipped"
    ├── --dry-run?                            →  status: "dry-run"
    │
    ▼
Fetch XML from API
    │
    ├── --in-force-only and isInForce=false?  →  status: "skipped-repealed"
    │
    ▼
Save main.xml to output directory
    │
    ├── --pdf?   →  Fetch and save main.pdf
    ├── --zip?   →  Fetch and save main.akn (ZIP package)
    └── --media? →  Extract media links from XML, fetch each file
    │
    ▼
status: "success"
```

**5. Record state and manifest**

After each document:
- `ManifestManager.add()` appends an entry to `manifest.json` with the URI, status,
  timestamp, file paths, and any error message
- `StateManager.mark_completed()` adds the URI to the completed set in `.state.json`

Both files are saved to disk immediately after every mutation.

**6. Resume interrupted downloads**

When `--resume` is passed:
- `.state.json` is loaded to recover `current_page`, `current_category`,
  `current_document_type`, and `completed_uris` (a set)
- The listing starts from the saved page number
- Already-completed URIs are skipped via O(1) set lookup

### Rate limiting and retry

The HTTP client enforces:
- **Sleep between requests:** 5 seconds by default (`--sleep`), measured from end of
  last request. If a request takes 1s, the client waits 4s before the next one.
- **Retry on failure:** Up to 5 retries with exponential backoff (1s, 2s, 4s, 8s, 16s)
  for HTTP 429, 500, 502, 503, 504.
- **Timeout:** 30 seconds per request.

### Output structure

```
finlex-data/
├── act/
│   └── statute-consolidated/
│       └── 1999/731/fin@20180817/
│           ├── main.xml          ← AKN XML
│           ├── main.pdf          ← (if --pdf)
│           └── media/            ← (if --media)
│               └── image1.gif
├── manifest.json                 ← audit log of all downloads
└── .state.json                   ← resume checkpoint
```

---

## 2. Convert Flow (`finlex-converter`)

```
┌───────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐
│ Find XML  │───▶│ Parse XML │───▶│  Render  │───▶│  Build    │
│   files   │    │ to struct │    │ Markdown │    │  index    │
└───────────┘    └───────────┘    └──────────┘    └───────────┘
      │                │                │                │
      ▼                ▼                ▼                ▼
  finlex-data/    Statute object   statute.md       index.json
  **/main.xml     (dataclass)    (per statute)   (citation map)
```

### Step-by-step

**1. Find XML files**

The converter walks the input directory (`finlex-data/`) looking for `main.xml` files.
If `--category` is set (e.g., `act`), it only searches within that subdirectory.

**2. Parse XML → Statute dataclass**

Each XML file is parsed with lxml using namespace-aware XPath into a hierarchy of
dataclasses:

```
Statute
├── metadata
│   ├── title           "Suomen perustuslaki"
│   ├── doc_number      "731/1999"
│   ├── eli             "http://data.finlex.fi/eli/sd/1999/731/ajantasa"
│   ├── date_issued     "1999-06-11"
│   ├── subtype         "statute-consolidated"
│   ├── language        "fin"
│   └── type_statute, category_statute, year, number
├── preamble            "Eduskunnan päätöksen mukaisesti..."
├── chapters[]
│   └── Chapter
│       ├── num         "1 luku"
│       ├── heading     "Valtiojärjestyksen perusteet"
│       └── sections[]
│           └── Section
│               ├── num         "1 §"
│               ├── heading     "Valtiosääntö"
│               └── subsections[]
│                   └── Subsection
│                       └── content  "Suomi on täysivaltainen tasavalta."
├── sections[]          (top-level, when no chapters exist)
├── entry_into_force    "Tämä laki tulee voimaan 1 päivänä maaliskuuta 2000."
└── conclusions
```

Metadata is extracted from `FRBRWork` (number, dates), `FRBRExpression` (language, ELI),
`preface` (title, doc number), and `proprietary` (finlex-specific fields).

**3. Render Markdown**

The renderer converts the Statute dataclass to Markdown with this heading hierarchy:

| XML element | With chapters | Without chapters |
|-------------|--------------|-----------------|
| Chapter     | `## 1 luku — Heading` | — |
| Section     | `### 1 § Heading` | `## 1 § Heading` |
| Subsection  | Plain paragraph | Plain paragraph |

A complete rendered file looks like:

```markdown
# Suomen perustuslaki

**Citation:** 731/1999
**Type:** statute-consolidated
**Language:** fin
**Date issued:** 1999-06-11
**ELI:** http://data.finlex.fi/eli/sd/1999/731/ajantasa

---

Eduskunnan päätöksen mukaisesti...

---

## 1 luku — Valtiojärjestyksen perusteet

### 1 § Valtiosääntö

Suomi on täysivaltainen tasavalta.

Suomen valtiosääntö on vahvistettu tässä perustuslaissa...

---

**Voimaantulo:** Tämä laki tulee voimaan 1 päivänä maaliskuuta 2000.
```

The output preserves the input directory structure:

```
finlex-data/act/statute-consolidated/1999/731/fin@20180817/main.xml
→ finlex-md/act/statute-consolidated/1999/731/fin@20180817/statute.md
```

**4. Build citation index**

After all files are converted, the indexer walks the XML files again to build
`index.json` — a lookup table mapping Finnish citation strings to file paths:

```json
{
  "731/1999": {
    "citation": "731/1999",
    "title": "Suomen perustuslaki",
    "path": "act/statute-consolidated/1999/731/fin@20180817/statute.md",
    "subtype": "statute-consolidated",
    "eli": "http://data.finlex.fi/eli/sd/1999/731/ajantasa",
    "date_issued": "1999-06-11"
  }
}
```

### Citation format

Finnish statute citations use `number/year` format (e.g., `731/1999`), but the API path
uses `year/number` (reversed). The `citations.py` module handles this mapping:

```
Citation "731/1999"
  → API path: /akn/fi/act/statute-consolidated/1999/731/fin@
  → Folder:   act/statute-consolidated/1999/731/fin@
```

---

## 3. End-to-End Example

Download all currently effective consolidated Finnish statutes and convert to Markdown:

```bash
# Step 1: Download (~25K in-force statutes, XML only)
finlex-downloader --types act --subtypes statute-consolidated \
  --lang fin@ --years 300 --in-force-only

# Step 2: Convert to Markdown with citation index
finlex-converter --input ./finlex-data --output ./finlex-md --category act
```

Result:
- `finlex-data/` — Raw AKN XML files + manifest + state
- `finlex-md/` — One Markdown file per statute + `index.json` citation map
