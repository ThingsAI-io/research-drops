---
name: feed-aggregator
description: Format filtered feed entries into structured digest reports using templates with FOR_EACH loops. Use when generating publication-ready summaries from pre-filtered content.
---

# Feed Aggregator Skill

This skill provides capabilities for formatting filtered and scored feed entries into structured digest reports for publication as GitHub Discussions, markdown files, or other formats using a template-based FOR_EACH loop system.

## When to Use This Skill

Use this skill when:
- Formatting filtered feed entries into digest reports
- Generating publication-ready summaries
- Creating weekly/daily digest reports
- Applying templates with loops to structured data
- Publishing aggregated content summaries

## Required Context

Before using this skill, ensure you have:
- Filtered feed entries (from feed-filter skill) with:
  - Title, link, description
  - Relevance category (High/Medium/Low)
  - Matched topics and ideas
- Template file: `.github/skills/feed-aggregator/templates/weekly-digest-template.md`
- Current date for digest title

## Core Operations

### 1. Load Template

**Purpose**: Load formatting template with FOR_EACH loop markers

**Template location**: `.github/skills/feed-aggregator/templates/weekly-digest-template.md`

**Template structure**:
The template uses FOR_EACH loops to define how each entry should be formatted:

```markdown
## High Relevance ({HIGH_COUNT})

<!-- FOR_EACH entry IN high_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
  - Related to: {ENTRY_TOPICS}
<!-- END_FOR_EACH -->
```

**Document-level placeholders**:
- `{DATE}`: Current date (YYYY-MM-DD)
- `{DATE_RANGE}`: Date range covered
- `{TOTAL_ENTRIES}`: Total entries analyzed
- `{HIGH_COUNT}`, `{MEDIUM_COUNT}`, `{LOW_COUNT}`: Category counts

**Entry-level placeholders** (within FOR_EACH blocks):
- `{ENTRY_TITLE}`: Entry title
- `{ENTRY_LINK}`: Direct link to article
- `{ENTRY_CONTRIBUTION_TYPE}`: Category of contribution (see taxonomy below)
- `{ENTRY_KEY_CONTRIBUTION}`: 1-3 sentence summary of what the paper actually contributes
- `{ENTRY_TOPICS}`: Comma-separated matched topics

### 2. Parse FOR_EACH Loop Markers

**Purpose**: Identify loop regions in template

**Process**:
1. Scan template for `<!-- FOR_EACH entry IN category -->` markers
2. Extract content between `<!-- FOR_EACH -->` and `<!-- END_FOR_EACH -->`
3. Store loop template for each category
4. Note the placeholder positions

**Categories supported**:
- `high_relevance_entries`
- `medium_relevance_entries`
- `low_relevance_entries`

**Example parsing**:
```
Found FOR_EACH loop for: high_relevance_entries
Loop template:
  - [{ENTRY_TITLE}]({ENTRY_LINK})
    - {ENTRY_KEY_CONTRIBUTION}
    - Related to: {ENTRY_TOPICS}
```

### 3. Generate Entry Content

**Purpose**: Extract and prepare data for each entry placeholder

**For each filtered entry, generate**:

**{ENTRY_CONTRIBUTION_TYPE}**:

Classify each entry into exactly one contribution type:

| Type | When to use | Example signal in abstract |
|------|------------|---------------------------|
| **Empirical study** | Reports results from experiments, user studies, surveys, or data analysis | "We conducted...", "N=...", "results show...", "participants..." |
| **Systematic review** | Surveys, meta-analyses, or literature synthesis across multiple works | "We review...", "survey of...", "meta-analysis", "N papers..." |
| **Framework** | Proposes a conceptual model, taxonomy, theoretical structure, or methodology | "We propose a framework...", "taxonomy of...", "model for..." |
| **Technical system** | Describes a built tool, pipeline, platform, or implementation | "We present a system...", "our tool...", "pipeline for..." |
| **Position paper** | Essay, commentary, editorial, or opinion piece arguing a viewpoint | "We argue...", "in this essay...", "we contend..." |
| **Case study** | In-depth analysis of a specific deployment, organization, or instance | "We examine the case of...", "deployed at...", "in practice at..." |
| **Policy/Governance** | Regulatory analysis, governance frameworks, standards, or guidelines | "Regulation...", "policy implications...", "governance of..." |

When ambiguous, prefer the type that best describes the *primary* contribution. A paper can have empirical results AND propose a framework — pick whichever dominates.

**{ENTRY_KEY_CONTRIBUTION}**:
- Summarize what the paper actually contributes in 1-3 sentences
- Focus on findings, claims, or artifacts — not just topic area
- Be specific: "Finds that AI-assisted writing reduces idea diversity by 25% across 1,000 participants" is better than "Studies AI's impact on writing"
- For empirical studies, mention key findings or effect sizes when available
- For frameworks, name the core abstraction or model
- For reviews, mention scope (N papers, time range, domains covered)

**{ENTRY_TOPICS}**:
- Join matched topic names with commas
- Example: "AI Ethics and Governance, AI Impact on Human Communication"

### 4. Apply FOR_EACH Loops

**Purpose**: Process loops to generate formatted entries

**Algorithm**:
1. For each FOR_EACH loop in template:
   a. Get the category (e.g., high_relevance_entries)
   b. Get filtered entries for that category
   c. Get loop template content
   d. For each entry in category:
      - Duplicate loop template
      - Replace entry placeholders with entry data
      - Append to output buffer
   e. Replace entire FOR_EACH block with output buffer

**Example**:
```
Input template:
<!-- FOR_EACH entry IN high_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK})
  - **{ENTRY_CONTRIBUTION_TYPE}** — {ENTRY_KEY_CONTRIBUTION}
  - Related to: {ENTRY_TOPICS}
<!-- END_FOR_EACH -->

With 2 entries:
Entry 1: title="Homogenization Effects of AI", type="Empirical study",
         contribution="Finds AI writing assistants reduce idea diversity by 25%..."
Entry 2: title="Governing Autonomous Agents", type="Policy/Governance",
         contribution="Proposes a three-tier regulatory framework for agent economies..."

Output:
- [Homogenization Effects of AI](https://arxiv.org/abs/123)
  - **Empirical study** — Finds AI writing assistants reduce idea diversity by 25%
    across 1,000 participants in a controlled experiment.
  - Related to: AI Impact on Human Cognition, AI Ethics and Governance
- [Governing Autonomous Agents](https://cacm.acm.org/article/456)
  - **Policy/Governance** — Proposes a three-tier regulatory framework separating
    agent capability licensing, deployment accountability, and outcome liability.
  - Related to: AI Ethics and Governance, AI Impact on Economy and Labor
```

### 5. Replace Document-Level Placeholders

**Purpose**: Populate document-level placeholders after processing loops

**Replacements**:
- `{DATE}` → Current date (e.g., "2026-02-07")
- `{DATE_RANGE}` → Calculated range (e.g., "January 31 - February 7, 2026")
- `{TOTAL_ENTRIES}` → Total count from filtering
- `{HIGH_COUNT}` → Count of high-relevance entries
- `{MEDIUM_COUNT}` → Count of medium-relevance entries
- `{LOW_COUNT}` → Count of low-relevance entries

**Calculation of DATE_RANGE**:
- Find earliest entry date across all categories
- Find latest entry date
- Format as "Month DD - Month DD, YYYY"
- If all entries from same week, use that week's range

### 6. Handle Empty Categories

**Purpose**: Gracefully handle categories with no entries

**Approach**:
When a category has zero entries, the FOR_EACH loop produces empty output:
- The section heading remains with "(0)"
- No entries appear below it
- This gives clear visibility that category was checked but empty

**Alternative** (optional):
Can remove entire section if count is zero during replacement phase.

### 7. Validate Output

**Purpose**: Ensure digest quality before publication

**Validation checks**:
- ✅ All document placeholders replaced
- ✅ All FOR_EACH loops processed
- ✅ All entry placeholders within loops replaced
- ✅ Links are functional (start with http)
- ✅ Markdown syntax valid
- ✅ No leftover markers (`<!--`, `{ENTRY_`)
- ✅ Counts match actual entries
- ✅ Every entry has a contribution type from the taxonomy
- ✅ Key contributions are specific (not generic topic descriptions)

**Common issues to catch**:
- Unclosed markdown links
- Leftover `{ENTRY_*}` placeholders
- FOR_EACH markers still present
- Mismatched counts
- Generic key contributions ("Studies AI" instead of specific findings)

### 8. Generate Final Output

**Purpose**: Produce publication-ready digest

**Output format options**:

**For GitHub Discussions**:
```yaml
create-discussion:
  title: "Weekly AI Research Digest - 2026-02-07"
  body: "[Processed template content]"
  category: "General"
```

**For file output**:
- Path: `workspace/digests/YYYY-MM-DD-digest.md`
- Format: Pure markdown

## Template Customization

Users can customize entry format by editing the template file:

### Changing Entry Format

Edit content between `<!-- FOR_EACH -->` and `<!-- END_FOR_EACH -->`:

**Example 1: Compact format**
```markdown
<!-- FOR_EACH entry IN high_relevance_entries -->
- [{ENTRY_TITLE}]({ENTRY_LINK}) — **{ENTRY_CONTRIBUTION_TYPE}**: {ENTRY_KEY_CONTRIBUTION}
<!-- END_FOR_EACH -->
```

**Example 2: Detailed format**
```markdown
<!-- FOR_EACH entry IN high_relevance_entries -->
### {ENTRY_TITLE}

**Link**: {ENTRY_LINK}
**Type**: {ENTRY_CONTRIBUTION_TYPE}
**Key Contribution**: {ENTRY_KEY_CONTRIBUTION}
**Related Topics**: {ENTRY_TOPICS}

---
<!-- END_FOR_EACH -->
```

### Adding Custom Fields

To add new entry fields:
1. Update feed-filter to output new field
2. Add placeholder to template (e.g., `{ENTRY_AUTHORS}`)
3. Update this skill to populate placeholder

## Integration with Skills

**Input from**: feed-filter skill
- Receives filtered, scored, categorized entries

**Output to**: Publishing mechanism
- GitHub Discussions (via safe-outputs)
- File system (markdown files)

**Workflow**:
```
feed-parser → feed-filter → feed-aggregator → publish
(parse XML)   (score/filter) (format with loops) (create discussion)
```

## Success Criteria

A successful aggregation:
- ✅ Loads template successfully
- ✅ Parses all FOR_EACH loops correctly
- ✅ Processes all entries through loops
- ✅ Replaces all placeholders (document and entry level)
- ✅ Validates output quality
- ✅ Produces publication-ready digest
- ✅ Respects user-defined formatting in template
