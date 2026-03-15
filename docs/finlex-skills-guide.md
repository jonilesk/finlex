# Finlex Skills — Finnish Law Knowledge Base for AI Agents

This document describes the `finlex-skills/` folder structure, data format, and how to use it as a knowledge base for AI agents.

## Overview

`finlex-skills/` contains **4,164 Finnish statutes** (laws and key decrees) converted from official Finlex XML (Akoma Ntoso format) into clean Markdown with machine-readable YAML frontmatter. The data is organized into **13 topic-based skill folders** that map to Finnish government ministry domains.

All statutes are **consolidated (ajantasainen)** — meaning they reflect the current in-force version of the law, with all amendments integrated.

## Folder Structure

```
finlex-skills/
├── README.md                              # Overview with statistics
├── index.json                             # Master citation → metadata lookup
│
├── tyolainsaadanto/                       # Employment & industry law (180 files)
│   ├── README.md                          # Skill description + full law listing
│   ├── _index.json                        # Citation index for this folder
│   ├── tyovoima-ja-tyosuhteet/            # Employment, working hours, co-determination
│   ├── elinkeinot-ja-energia/             # Energy markets, chemicals, industry regulation
│   └── hankinnat-ja-kilpailu/             # Public procurement, competition
│
├── sosiaali-ja-terveys/                   # Health & social affairs (363 files)
│   ├── terveydenhuolto/                   # Healthcare, medical devices, infectious diseases
│   ├── elakkeet-ja-vakuutukset/           # Pensions, insurance, workers' compensation
│   ├── sosiaalipalvelut/                  # Social services, child protection, disability
│   └── turvallisuus-ja-valvonta/          # Radiation, tobacco, alcohol, food safety
│
├── talous-ja-verotus/                     # Finance & taxation (823 files)
│   ├── verotus/                           # Tax laws (income, VAT, excise, vehicle)
│   ├── rahoitusmarkkinat/                 # Financial markets, investment funds, AML
│   ├── kuntahallinto/                     # Municipal governance, wellbeing regions
│   └── julkinen-talous/                   # Customs, public finance
│
├── oikeus/                                # Justice & legal system (332 files)
│   ├── oikeudenkäynti/                    # Court proceedings, judicial administration
│   ├── rikos-ja-rangaistus/               # Criminal law, sentencing, community sanctions
│   ├── yksityisoikeus/                    # Private law, foundations, data protection
│   └── kansainvalinen-oikeus/             # International legal cooperation
│
├── liikenne-ja-viestinta/                 # Transport & communications (272 files)
│   ├── tieliikenne/                       # Road traffic, vehicles, driver's licenses
│   ├── raideliikenne-ja-merenkulku/       # Rail, maritime, pilotage, aviation
│   └── viestinta-ja-kyberturvallisuus/    # Communications, cyber security, digital
│
├── ymparisto-ja-rakentaminen/             # Environment & construction (162 files)
│   ├── rakentaminen/                      # Building permits, construction regulation
│   ├── luonnonsuojelu/                    # Nature conservation, environmental protection
│   └── asuminen/                          # Housing, rental, right-of-occupancy
│
├── maatalous-ja-metsa/                    # Agriculture & forestry (280 files)
│   ├── elaimet-ja-elintarvikkeet/         # Animal welfare, food safety, feed
│   ├── maataloustuet/                     # Agricultural subsidies, EU implementation
│   └── metsa-ja-kalastus/                 # Forestry, fishing, game management
│
├── koulutus-ja-kulttuuri/                 # Education & culture (155 files)
│   ├── koulutus/                          # Schools, universities, vocational training
│   ├── kirkko/                            # Church legislation (evangelical-lutheran)
│   └── kulttuuri-ja-nuoriso/              # Culture, youth, sports, libraries
│
├── sisaasiat/                             # Internal affairs (105 files, flat)
├── ulkoasiat/                             # Foreign affairs (462 files)
│   ├── merkittavat/                       # Substantive laws (>10KB)
│   └── sopimukset/                        # Treaty ratification laws
│
├── puolustus/                             # Defence (64 files, flat)
├── valtionhallinto/                       # Government administration (7 files, flat)
└── yleinen/                               # General / unclassified (959 files, flat)
```

## File Format

Every statute is a single Markdown file with YAML frontmatter:

```markdown
---
citation: "872/2019"
title: "Työaikalaki"
type: act
ministry: "Työ- ja elinkeinoministeriö"
ministry_id: fi.ministry-of-economic-affairs-and-employment
eli: http://data.finlex.fi/eli/sd/2019/872/ajantasa
date_issued: 2019-07-05
date_published: 2019-07-11
language: fin
skill: tyolainsaadanto
subtopic: tyovoima-ja-tyosuhteet
issued_under: ["55/2001"]
---

# Työaikalaki

Eduskunnan päätöksen mukaisesti säädetään:

---

## 1 luku — Soveltamisala

### 1 § Yleinen soveltamisala

Tätä lakia sovelletaan työsopimuslain (55/2001) 1 luvun 1 §:ssä
tarkoitetun työsopimuksen sekä virkasuhteen perusteella tehtävään työhön...

### 2 § Poikkeukset soveltamisalasta

...
```

### Frontmatter Fields

| Field | Type | Description |
|-------|------|-------------|
| `citation` | string | Official citation (e.g., `"872/2019"` = law 872 of year 2019) |
| `title` | string | Finnish title of the statute |
| `type` | string | `act` (laki) or `decree` (asetus) |
| `ministry` | string | Responsible ministry in Finnish |
| `ministry_id` | string | Machine-readable ministry identifier |
| `eli` | string | European Legislation Identifier URL |
| `date_issued` | string | Date the law was enacted (YYYY-MM-DD) |
| `date_published` | string | Date published in statute collection |
| `language` | string | Always `fin` (Finnish) |
| `skill` | string | Top-level skill folder name |
| `subtopic` | string | Sub-folder name (empty if in skill root) |
| `issued_under` | list | Citations of parent laws this was issued under |

### Body Structure

- **`# Title`** — statute name (H1)
- **`## N luku — Heading`** — chapter (H2), for laws with chapters
- **`### N § Heading`** — section / pykälä (H3, or H2 if no chapters)
- **`## Heading`** — cross-heading section divider (in laws without formal chapters)
- Subsections (momentti) are plain paragraphs under their section
- Preamble and entry-into-force blocks are separated by `---` dividers

## Index Files

### `index.json` (master, root level)

Maps every citation to its metadata and file path:

```json
{
  "872/2019": {
    "citation": "872/2019",
    "title": "Työaikalaki",
    "path": "tyolainsaadanto/tyovoima-ja-tyosuhteet/872-2019.md",
    "type": "act",
    "ministry": "Työ- ja elinkeinoministeriö",
    "skill": "tyolainsaadanto",
    "subtopic": "tyovoima-ja-tyosuhteet",
    "eli": "http://data.finlex.fi/eli/sd/2019/872/ajantasa",
    "date_issued": "2019-07-05",
    "xml_size": 129000
  }
}
```

### `_index.json` (per skill folder)

Same structure, scoped to that folder's statutes only.

### `README.md` (per skill folder)

Human-readable overview with skill description, sub-topic listing, and a table of all statutes sorted by size.

## How to Use as AI Agent Skills

### Option 1: Folder-per-Skill (Recommended)

Point each skill/tool at one top-level folder. The agent gets domain-specific Finnish law knowledge:

```yaml
# Example: Copilot skill definition
skills:
  - name: tyolainsaadanto
    description: "Finnish employment and industry law"
    path: ./finlex-skills/tyolainsaadanto/
  - name: sosiaali-ja-terveys
    description: "Finnish health and social affairs law"
    path: ./finlex-skills/sosiaali-ja-terveys/
```

Each folder is self-contained — it has a README, index, and all the Markdown files the agent needs.

### Option 2: Sub-Topic Granularity

For more focused skills, point at sub-folders:

```yaml
skills:
  - name: verotus
    description: "Finnish tax law"
    path: ./finlex-skills/talous-ja-verotus/verotus/
  - name: tieliikenne
    description: "Finnish traffic law"
    path: ./finlex-skills/liikenne-ja-viestinta/tieliikenne/
```

### Option 3: Citation Lookup via Index

Use `index.json` to find specific laws programmatically:

```python
import json

with open("finlex-skills/index.json") as f:
    index = json.load(f)

# Find a law by citation
entry = index.get("872/2019")
if entry:
    with open(f"finlex-skills/{entry['path']}") as f:
        law_text = f.read()
```

### Option 4: YAML Frontmatter Filtering

Parse frontmatter to filter/select laws dynamically:

```python
import yaml
from pathlib import Path

# Find all tax acts
for md_file in Path("finlex-skills/talous-ja-verotus/verotus").rglob("*.md"):
    text = md_file.read_text()
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        meta = yaml.safe_load(fm)
        if meta.get("type") == "act":
            print(f"{meta['citation']} — {meta['title']}")
```

## Statistics

| Skill Folder | Finnish Name | Acts | Decrees | Total |
|---|---|---|---|---|
| `talous-ja-verotus` | Talous- ja verolainsäädäntö | 763 | 60 | 823 |
| `yleinen` | Yleinen lainsäädäntö | 958 | 1 | 959 |
| `ulkoasiat` | Ulkoasioiden lainsäädäntö | 459 | 3 | 462 |
| `sosiaali-ja-terveys` | Sosiaali- ja terveyslainsäädäntö | 289 | 74 | 363 |
| `oikeus` | Oikeuslainsäädäntö | 303 | 29 | 332 |
| `maatalous-ja-metsa` | Maatalous- ja metsälainsäädäntö | 144 | 136 | 280 |
| `liikenne-ja-viestinta` | Liikenne- ja viestintälainsäädäntö | 245 | 27 | 272 |
| `tyolainsaadanto` | Työlainsäädäntö | 123 | 57 | 180 |
| `ymparisto-ja-rakentaminen` | Ympäristö- ja rakentamislainsäädäntö | 93 | 69 | 162 |
| `koulutus-ja-kulttuuri` | Koulutus- ja kulttuurilainsäädäntö | 131 | 24 | 155 |
| `sisaasiat` | Sisäasioiden lainsäädäntö | 77 | 28 | 105 |
| `puolustus` | Puolustuslainsäädäntö | 56 | 8 | 64 |
| `valtionhallinto` | Valtionhallinnon lainsäädäntö | 7 | 0 | 7 |
| **Total** | | **3,648** | **516** | **4,164** |

## Data Source & Freshness

- **Source:** [Finlex Open Data API](https://data.finlex.fi/) — official Finnish government legal database
- **Format:** Akoma Ntoso XML (AKN 3.0), converted to Markdown
- **Scope:** Consolidated statutes (`ajantasainen säädöskokoelma`) — all amendments merged
- **Coverage:** All in-force Finnish acts (laki) with substantive content, plus key decrees (asetus) over 20KB
- **Filtered out:** Budget amendments, administrative announcements, office creation laws, decisions, and other procedural documents

### Regenerating

To regenerate from source XML:

```bash
pip install -e ".[dev]"
finlex-skills -i ./finlex-data -o ./finlex-skills
```

## Key Concepts for Non-Finnish Teams

| Finnish Term | English | In This Dataset |
|---|---|---|
| **Laki** | Act / Law | `type: act` — primary legislation passed by Parliament |
| **Asetus** | Decree / Regulation | `type: decree` — implementing regulation by government/ministry |
| **Pykälä (§)** | Section | The basic unit of Finnish law (`### 1 §`) |
| **Momentti** | Subsection | Numbered paragraphs within a section |
| **Luku** | Chapter | Groups of sections (`## 1 luku — Heading`) |
| **Säädöskokoelma** | Statute Collection | Official publication of Finnish laws |
| **Ajantasainen** | Consolidated | Current version with all amendments integrated |
| **Voimaantulo** | Entry into force | When the law becomes effective |
| **ELI** | European Legislation Identifier | Standardized URL for the law |
| **Citation (N/YYYY)** | Official reference | E.g., `55/2001` = law #55 of year 2001 |
