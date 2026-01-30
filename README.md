# Finlex Downloader

Download Akoma Ntoso documents from the Finnish Finlex Open Data API.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Basic usage

Download Finnish statutes from the current year:

```bash
finlex-downloader --types act --years 1 --pdf
```

### Download multiple document types

```bash
finlex-downloader --types act judgment doc --years 2
```

### Per-type year settings

Download 5 years of acts but only 2 years of judgments:

```bash
finlex-downloader --types act judgment \
  --years-act 5 \
  --years-judgment 2
```

### Dry run

See what would be downloaded without actually downloading:

```bash
finlex-downloader --types act --years 1 --dry-run
```

### Resume interrupted download

```bash
finlex-downloader --types act --years 1 --resume
```

### All options

```bash
finlex-downloader --help
```

```
usage: finlex-downloader [-h] [-o OUTPUT] 
                         [--types {act,judgment,doc,authority-regulation} ...]
                         [--years YEARS] 
                         [--years-act YEARS_ACT]
                         [--years-judgment YEARS_JUDGMENT]
                         [--years-doc YEARS_DOC]
                         [--years-authority-regulation YEARS]
                         [--lang LANG] [--limit LIMIT] [--max-pages MAX_PAGES]
                         [--sleep SLEEP] [--pdf] [--zip] [--media]
                         [--force] [--dry-run] [--resume] [--reset] [-v]

Options:
  -o, --output          Output directory (default: ./finlex-data)
  --types               Document categories: act, judgment, doc, authority-regulation
  --years               Number of years to download (default: 1)
  --years-act           Override years for act category
  --years-judgment      Override years for judgment category
  --years-doc           Override years for doc category
  --years-authority-regulation  Override years for authority-regulation
  --lang                Language marker (default: fin@)
  --limit               Page size (default: 10, max: 10)
  --max-pages           Maximum pages per document type
  --sleep               Seconds between requests (default: 5)
  --pdf                 Also download PDF versions
  --zip                 Also download ZIP packages
  --media               Also download media files
  --force               Re-download existing files
  --dry-run             Show actions without downloading
  --resume              Resume from last checkpoint
  --reset               Reset state and start fresh
  -v, --verbose         Verbose output
```

## Output structure

```
finlex-data/
  act/
    statute/
      2024/123/fin@/
        main.xml
        main.pdf
        media/
    statute-consolidated/
      ...
  judgment/
    kko/
      ...
  doc/
    government-proposal/
      ...
  manifest.json
  .state.json
```

## Rate limiting

The Finlex API may return HTTP 429 if you make too many requests. The downloader:

- Waits 5 seconds between requests by default (`--sleep`)
- Automatically retries with exponential backoff on 429/5xx errors
- Saves state for resuming interrupted downloads

## Document types

### act
- `statute` - Original statutes
- `statute-consolidated` - Consolidated statutes
- `statute-translated` - Translated statutes
- `statute-aland` - Åland statutes
- `statute-sami` - Sámi statutes

### judgment
- `kko` - Supreme Court decisions
- `kho` - Supreme Administrative Court decisions

### doc
- `government-proposal` - Government proposals
- `treaty` - Treaties
- `treaty-consolidated` - Consolidated treaties
- `authority-regulation` - Authority regulations

## Development

### Run tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=finlex_downloader --cov-report=term-missing
```

## License

MIT
