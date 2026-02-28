---
name: feed-filter
description: Filter feed entries by relevance to topics of interest using two-phase judgment (titles then abstracts) and annotate with idea connections. Use when curating content against defined interests.
---

# Feed Filter Skill

Filter feed entries through two sequential phases — a broad title scan followed by selective abstract review — then annotate survivors with idea connections. Replaces keyword matching with judgment-based relevance assessment.

## When to Use

- Filtering downloaded feed entries against topics of interest
- Curating a feed batch before aggregation or publication
- Preparing a relevance-scored shortlist for the feed-aggregator skill

## Required Inputs

| Input | Location | Purpose |
|-------|----------|---------|
| Titles index | `{feed-dir}/titles.jsonl` | Lightweight first-pass scan |
| Entry files | `{feed-dir}/{entry_id}.md` | Full abstract for second-pass |
| Topics | `workspace/topics.yml` | Relevance criteria |
| Ideas | `workspace/ideas/*.md` | Annotation (not filtering) |

The `titles.jsonl` file is produced by `download_feed.py`. Each line is a JSON object:
```json
{"entry_id": "...", "title": "...", "link": "...", "date": "...", "authors": "...", "feed_id": "..."}
```

## Workflow

```
titles.jsonl ──► Phase 1: Title Scan (broad) ──► Phase 2: Abstract Review (selective) ──► Ideas Annotation ──► Output
```

### Phase 1: Title Scan

**Goal**: Cast a wide net. From dozens or hundreds of titles, select the ones that _might_ be relevant based on title alone.

**Input**: Read `titles.jsonl` — one JSON object per line.

**Process**:
1. Read `workspace/topics.yml`. Internalize each topic's name, description, and positive/negative signals.
2. Read all titles from `titles.jsonl`.
3. For each title, make a **judgment call**: "Given the topics I care about, could this be relevant?"
   - This is NOT keyword matching. Use semantic judgment.
   - A title like "Who Owns an AI Agent's Identity?" is obviously relevant even if no keyword fires.
   - A title like "Efficient Transformer Training on TPU Clusters" is obviously not.
4. Apply the **human-interest test**: "Would someone interested in what AI means for people, identity, work, communication, and society want to read this?"
5. When uncertain, **include** — Phase 2 will be selective.

**Output**: A shortlist of entry_ids that passed title scan.

**Guidance for judgment calls**:
- Titles suggesting human, societal, economic, philosophical, ethical, or identity dimensions → **include**
- Titles that are clearly pure technical optimization, benchmarking, architecture engineering → **exclude**
- Titles that are ambiguous or could go either way → **include** (let Phase 2 decide)
- Expect to pass roughly 10-30% of entries through to Phase 2

### Phase 2: Abstract Review

**Goal**: Selective filtering using full abstract content. This is where rigor happens.

**Input**: For each entry_id from the Phase 1 shortlist, read the corresponding `{entry_id}.md` file.

**Process**:
1. Read the full entry file (frontmatter + abstract/description).
2. Assess relevance against topics using **positive and negative signals** from `workspace/topics.yml`:
   - Check negative signals first — if the abstract reveals this is a benchmark paper, optimization study, or pure systems paper despite a promising title, **exclude**.
   - Then confirm via positive signals — does the abstract's framing, questions, or findings align with what makes the topic interesting?
3. Assign a **relevance tier**:
   - **High**: Directly addresses one or more topics. Clear human/societal/identity dimension. Worth reading in full.
   - **Medium**: Touches a topic but isn't centered on it. Potentially useful context or methodology.
   - **Low**: Tangentially related. Might yield one useful insight but not core reading.
   - **Exclude**: False positive from Phase 1 — abstract reveals it's not actually relevant.
4. For each non-excluded entry, record:
   - Matched topics (which ones and why)
   - Relevance tier
   - One-line rationale

**Key disambiguation rules** (apply during abstract review):
- The word "agent" alone is NOT a relevance signal
- Papers primarily about benchmarks, simulation frameworks, ML architectures, or training procedures → exclude unless they explicitly address human/societal dimensions
- Technical optimization papers (efficiency, accuracy, scaling) → exclude
- If the primary contribution is a new method/algorithm/framework evaluated on benchmarks → exclude

### Phase 3: Ideas Annotation

**Goal**: Enrich surviving entries with connections to existing ideas. This is **annotation only** — it does not filter or change tiers.

**Input**: Entries that passed Phase 2 (High, Medium, or Low tier).

**Process**:
1. Read all `.md` files in `workspace/ideas/`. Extract title, description, and tags from frontmatter.
2. For each surviving entry, check: does it resonate with any existing idea?
3. If yes, add a brief annotation: which idea, and what the connection is.
4. If no idea connection exists, that's fine — the entry is still relevant via topic matching.

**Output format per entry**:
```
ideas:
  - idea: "Kids AI Confidant"
    connection: "Explores AI mediating emotional relationships — directly relevant"
  - idea: "Agent-to-Agent Recruiter Alignment"
    connection: "Agent proxy communication patterns"
```

**Important**: An entry with zero idea connections but High topic relevance stays High. Ideas are context, not criteria.

## Output Format

Present results grouped by relevance tier. For each entry:

```
### High Relevance

**{title}**
- Authors: {authors}
- Date: {date}
- Link: {link}
- Topics: {matched topics with one-line rationale each}
- Ideas: {idea connections, if any}
- Entry file: {entry_id}.md

### Medium Relevance
...

### Low Relevance
...
```

**Sorting within tiers**:
1. Number of matched topics (descending)
2. Publication date (newest first)

### Excluded Entries Summary

After the tiered results, provide a summary of Phase 2 exclusions:

```
### Excluded in Phase 2 (N entries)
- "{title}" — {reason: e.g., "benchmark paper despite promising title"}
- "{title}" — {reason}
```

Do not list entries excluded in Phase 1 (there are too many and the reason is simply "not relevant by title").

### Filter Statistics

```
FILTER STATISTICS
-----------------
Total entries scanned: {N}
Passed title scan (Phase 1): {N} ({%})
After abstract review (Phase 2):
  High: {N}
  Medium: {N}
  Low: {N}
  Excluded: {N}
Entries with idea connections: {N}
Most matched topics: {top 3}
```

## Integration

**Upstream**: `download_feed.py` produces the `titles.jsonl` and per-entry `.md` files.
**Downstream**: feed-aggregator skill consumes the filtered, tiered, annotated entries.

```
download_feed.py → feed-filter → feed-aggregator
(fetch + JSONL)    (2-phase filter) (format digest)
```

## Operational Principles

1. **Judgment over keywords**: Phase 1 uses semantic judgment on titles, not string matching. You understand the topics — use that understanding.
2. **Broad then selective**: Phase 1 is generous (include if uncertain). Phase 2 is strict (exclude if abstract doesn't confirm).
3. **Ideas annotate, never filter**: Idea connections are valuable metadata but never determine inclusion or exclusion.
4. **Signals are your rubric**: In Phase 2, positive and negative signals from `topics.yml` are the primary tool. Use them as examples of what counts and what doesn't.
5. **Explain exclusions**: Every Phase 2 exclusion needs a reason. Phase 1 exclusions are implicit (not relevant by title).
6. **The human-interest test**: "Does this explore what AI means for people, not just for AI systems?" Apply at both phases.
