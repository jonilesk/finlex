<!-- markdownlint-disable-file -->
# Task Research: Finlex JSON Model

Research the contents of `finlex-data/`, what the repository already knows about Finnish law and Finlex XML, and define a practical JSON-oriented model for AI retrieval with reduced chunk bloat.

## Task Implementation Requests

* Inventory the current `finlex-data/` corpus and identify what document families, subtypes, metadata, and structure are actually present.
* Determine what is known from the codebase and docs about Finnish law, Finlex Open Data, Akoma Ntoso structure, and citation relations.
* Recommend a JSON target model suitable for storage, querying, and AI retrieval.
* Evaluate chunking strategies that reduce unnecessary structural bloat while preserving legal meaning and references.

## Scope and Success Criteria

* Scope: Existing downloaded `finlex-data/` corpus, repository docs/code/tests, and external high-level Finnish-law/Finlex domain facts relevant to data modeling.
* Assumptions:
  * The source of truth remains the original XML.
  * The target system is optimized for JSON storage and retrieval rather than XML-native querying.
  * The user wants lower-bloat chunks than raw Akoma Ntoso nesting.
* Success Criteria:
  * Clear inventory of what exists in `finlex-data/`.
  * Clear summary of what fields and relations can be extracted from the current XML.
  * One recommended JSON model with rationale.
  * One recommended chunking strategy with trade-offs.

## Outline

1. Inventory local corpus contents.
2. Summarize repository knowledge about Finlex XML and Finnish law.
3. Evaluate JSON conversion and chunking alternatives.
4. Select a recommended model and chunking approach.

## Potential Next Research

* Verify cross-document relation density across a wider sample.
  * Reasoning: Relation extraction strategy depends on how often inline refs and proprietary refs appear.
  * Reference: local `finlex-data` corpus

## Research Executed

### File Analysis

* Pending.

### Code Search Results

* Pending.

### External Research

* Pending.

### Project Conventions

* Source XML should remain authoritative; derived models should preserve provenance.
* Current parser selectively extracts metadata, chapters, sections, subsections, and some lifecycle fields.

## Key Discoveries

### Project Structure

Pending.

### Implementation Patterns

Pending.

### Complete Examples

```json
{
  "status": "pending"
}
```

### API and Schema Documentation

Pending.

### Configuration Examples

```json
{
  "status": "pending"
}
```

## Technical Scenarios

### JSON Target Model For Finlex Laws

Pending.

**Requirements:**

* Preserve citation, hierarchy, provenance, and explicit references.
* Reduce raw XML bloat for AI retrieval.
* Support structured filtering and text retrieval.

**Preferred Approach:**

* Pending.

```text
pending
```

**Implementation Details:**

Pending.

```json
{
  "status": "pending"
}
```

#### Considered Alternatives

Pending.
