---
name: research-filter
description: >
  Two-phase relevance filter for feed entries. Phase 1 scans titles broadly
  using semantic judgment against topics.yml. Phase 2 reads abstracts and
  applies positive/negative signals from topics.yml to tier entries
  (High/Medium/Low).
  Use when curating downloaded entries before passing to research-digest.
---

# Research Filter Skill

Two-phase filter: broad title scan → selective abstract review.
Uses `topics.yml` as the sole source of truth for what counts as relevant.

## When to Use

- Filtering downloaded research feed entries before digest generation
- Preparing a relevance-scored shortlist for research-digest

## Required Inputs

| Input | Location | Purpose |
|-------|----------|---------|
| Titles index | `{feed-dir}/titles.jsonl` | Phase 1 scan |
| Entry files | `{feed-dir}/{entry_id}.md` | Phase 2 abstract review |
| Topics | `conf/topics.yml` | Positive/negative signals for relevance |

`titles.jsonl` is produced by `fetch.py`. Each line:
```json
{"entry_id": "...", "title": "...", "link": "...", "date": "...", "authors": "...", "feed_id": "..."}
```

## Workflow

```
titles.jsonl → Phase 1 (broad) → Phase 2 (selective) → Output
```

### Phase 1: Title Scan

**Goal**: Broad pass — select titles that *might* be relevant. When uncertain, include.

1. Read `conf/topics.yml`. Internalize each topic's description and signals.
2. For each title in `titles.jsonl`, judge: "Given these topics, could this be relevant?"
   - Use semantic judgment, not keyword matching.
   - Positive signals from topics.yml → include.
   - Matches negative signals only → exclude.
   - Ambiguous → include (Phase 2 will decide).
3. Expect ~10-30% pass rate.

**Output**: Shortlist of entry_ids.

### Phase 2: Abstract Review

**Goal**: Strict filtering using full content. This is where the negative signals from `topics.yml` do their work.

For each shortlisted entry, read `{entry_id}.md`:

1. **Negative signals first**: Check each topic's `negative_signals`. If the abstract matches a negative signal pattern — exclude, regardless of promising keywords.
2. **Positive signals to confirm**: Does the abstract align with any topic's `positive_signals`? If no positive signal confirms relevance — exclude.
3. **Assign tier**:
   - **High**: Directly addresses ≥1 topic. Clear alignment with positive signals.
   - **Medium**: Touches a topic tangentially. Some positive signal match but not central.
   - **Low**: Weak connection. Might yield one useful insight.
   - **Exclude**: Negative signals triggered, or no positive signal confirmed.
4. Record: matched topics (which + why), tier, one-line rationale.

## Output Format

Group by tier:

```
### High Relevance

**{title}**
- Authors: {authors}
- Date: {date}
- Link: {link}
- Topics: {matched topics with one-line rationale each}
- Entry file: {entry_id}.md
```

Sort within tiers: matched topic count (desc), then date (newest first).

### Excluded Entries Summary

```
### Excluded in Phase 2 (N entries)
- "{title}" — {reason referencing specific negative signal from topics.yml}
```

Phase 1 exclusions are not listed (implicit: not relevant by title).

### Filter Statistics

```
Total entries scanned: {N}
Passed Phase 1: {N} ({%})
Phase 2: High {N} / Medium {N} / Low {N} / Excluded {N}
Top matched topics: {top 3}
```

## Integration

```
fetch.py → research-filter → research-digest
```

## Principles

1. **topics.yml is the rubric**: All relevance decisions trace back to its positive/negative signals. Do not invent criteria beyond what topics.yml defines.
2. **Broad then strict**: Phase 1 includes if uncertain. Phase 2 excludes unless positive signals confirm.
3. **Explain with signals**: Every Phase 2 exclusion cites the negative signal (or absent positive signal) that drove the decision.
