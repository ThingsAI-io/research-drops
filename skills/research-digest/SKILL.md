---
name: research-digest
description: >
  Format pre-filtered, relevance-scored feed entries into a publication-ready
  Markdown digest. Takes High/Medium/Low categorised entries (output of
  research-filter) and expands them through a FOR_EACH template, classifying each
  entry's contribution type and writing a specific key-contribution summary.
  Use AFTER research-filter has scored entries, not for raw/unfiltered feeds.
---

# Research Digest Skill

Formats filtered, scored research paper feed entries into a publication-ready digest using a
template with FOR_EACH loop markers.

## When to Use

- Turning scored entries (from research-filter) into a Markdown digest
- Publishing to GitHub Discussions or as a file

## Required Context

- Filtered entries with: title, link, description, relevance (High/Medium/Low), matched topics
- Template: `skills/research-digest/templates/weekly-digest-template.md`

## Template System

### Placeholders

**Document-level** — replaced once across the whole document:

| Placeholder | Value |
|---|---|
| `{DATE}` | Current date (YYYY-MM-DD) |
| `{DATE_RANGE}` | Earliest → latest entry date ("Feb 3–10, 2026") |
| `{TOTAL_ENTRIES}` | Total entries analyzed |
| `{HIGH_COUNT}` / `{MEDIUM_COUNT}` / `{LOW_COUNT}` | Per-category counts |

**Entry-level** — replaced per entry inside FOR_EACH blocks:

| Placeholder | Value |
|---|---|
| `{ENTRY_TITLE}` | Entry title |
| `{ENTRY_LINK}` | URL to article |
| `{ENTRY_CONTRIBUTION_TYPE}` | One of the contribution types below |
| `{ENTRY_KEY_CONTRIBUTION}` | 1-3 sentence specific summary (findings, claims, artefacts) |
| `{ENTRY_TOPICS}` | Comma-separated matched topic names |

### FOR_EACH Loops

The template wraps repeating sections in HTML comment markers:

```markdown
<!-- FOR_EACH entry IN high_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
<!-- END_FOR_EACH -->
```

**Processing**: for each entry in the named category, duplicate the inner
block, replace entry placeholders, and join the results. Empty categories
produce no output (the heading with "(0)" remains).

**Supported categories**: `high_relevance_entries`, `medium_relevance_entries`, `low_relevance_entries`

## Contribution Type Taxonomy

Classify each entry into exactly one type (pick whichever dominates):

| Type | Use when |
|---|---|
| **Empirical study** | Experiments, user studies, surveys, data analysis |
| **Systematic review** | Literature surveys, meta-analyses |
| **Framework** | Conceptual models, taxonomies, methodologies |
| **Technical system** | Tools, pipelines, platforms, implementations |
| **Position paper** | Commentary, editorials, opinion essays |
| **Case study** | In-depth analysis of a specific deployment or instance |
| **Policy/Governance** | Regulatory analysis, standards, guidelines |

## Writing Key Contributions

- Focus on specific findings, claims, or artefacts — not topic area
- Good: "Finds AI writing assistants reduce idea diversity by 25% across 1,000 participants"
- Bad: "Studies AI's impact on writing"
- Empirical → mention key findings / effect sizes
- Frameworks → name the core abstraction
- Reviews → mention scope (N papers, time range)

## Processing Steps

1. Load template from `skills/research-digest/templates/`
2. Parse FOR_EACH blocks (extract category + inner template)
3. For each category: expand entries, replace entry placeholders
4. Replace document-level placeholders
5. Validate: no leftover `{ENTRY_*}` or `<!-- FOR_EACH` markers, counts match, links start with http

## Output

Write the final Markdown to `/tmp/research-monitor/output.json`:

```json
{
  "title": "Weekly AI Research Digest - 2026-02-07",
  "body": "<processed markdown>"
}
```
