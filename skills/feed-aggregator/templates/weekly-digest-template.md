# Weekly AI Research Digest - {DATE}

This week's digest covers research published between {DATE_RANGE}. I analyzed {TOTAL_ENTRIES} entries from monitored feeds.

## High Relevance ({HIGH_COUNT})

<!-- FOR_EACH entry IN high_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
  - Related to: {ENTRY_TOPICS}
<!-- END_FOR_EACH -->

## Medium Relevance ({MEDIUM_COUNT})

<!-- FOR_EACH entry IN medium_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
  - Related to: {ENTRY_TOPICS}
<!-- END_FOR_EACH -->

## Low Relevance ({LOW_COUNT})

<!-- FOR_EACH entry IN low_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
<!-- END_FOR_EACH -->

---

**Summary**: Analyzed {TOTAL_ENTRIES} total entries. Found {HIGH_COUNT} high-relevance, {MEDIUM_COUNT} medium-relevance, and {LOW_COUNT} low-relevance papers related to our topics of interest.

---

## Template Instructions

This template uses a FOR_EACH loop structure to format entries. The feed-aggregator skill will:

1. Parse the `<!-- FOR_EACH ... -->` and `<!-- END_FOR_EACH -->` markers
2. For each entry in the specified category, duplicate the content between markers
3. Replace entry-level placeholders with actual entry data

### Document-Level Placeholders

- `{DATE}`: Current date in YYYY-MM-DD format
- `{DATE_RANGE}`: Date range covered by the digest (e.g., "February 3-10, 2026")
- `{TOTAL_ENTRIES}`: Total number of entries analyzed across all feeds
- `{HIGH_COUNT}`: Number of high-relevance entries
- `{MEDIUM_COUNT}`: Number of medium-relevance entries
- `{LOW_COUNT}`: Number of low-relevance entries

### Entry-Level Placeholders (used within FOR_EACH blocks)

- `{ENTRY_TITLE}`: Entry title
- `{ENTRY_LINK}`: Direct link to article
- `{ENTRY_CONTRIBUTION_TYPE}`: Category of contribution — one of: Empirical study, Systematic review, Framework, Technical system, Position paper, Case study, Policy/Governance
- `{ENTRY_KEY_CONTRIBUTION}`: 1-3 sentence summary of what the paper actually contributes (findings, claims, or artifacts — not just topic area)
- `{ENTRY_TOPICS}`: Comma-separated list of matched topic names

### Format Customization

You can customize the format of each entry by editing the content between `<!-- FOR_EACH -->` and `<!-- END_FOR_EACH -->` markers.

Examples:
- Change bullet depth or style
- Add/remove fields
- Reorder information
- Change how topics are displayed
