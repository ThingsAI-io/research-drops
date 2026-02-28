# RSS/Atom Feed Downloader

A deterministic Python script that downloads RSS or Atom feeds and outputs one Markdown file per entry. Part of the daily RSS monitor workflow.

## Purpose

This tool separates the **deterministic** feed-fetching phase from the **agentic** filtering phase. Instead of having a Copilot CLI agent waste compute on mechanical operations like `curl` and XML parsing, this script handles:

1. HTTP fetching with proper headers
2. RSS 2.0 / Atom format detection and parsing
3. Entry extraction (title, link, description, date, authors)
4. HTML stripping and entity decoding
5. Cutoff filtering (skip entries older than N hours)
6. Output as structured Markdown files with YAML frontmatter

The agent then reads these pre-structured files and focuses on what it's good at: judgment, filtering, and writing.

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install requests pyyaml
```

## Usage

### Basic Usage

```bash
python download_feed.py \
  --url "http://rss.arxiv.org/rss/cs.AI" \
  --output /tmp/research-monitor/feeds/arxiv-ai \
  --cutoff 24 \
  --feed-id arxiv-ai \
  --feed-name "arXiv Computer Science - Artificial Intelligence"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--url` | Yes | — | RSS or Atom feed URL |
| `--output` | Yes | — | Output directory (created if missing) |
| `--cutoff` | No | `24` | Hours to look back from now. Entries older than this are skipped. Use `0` for no cutoff. |
| `--feed-id` | No | derived from URL | Identifier used in output filenames and metadata |
| `--feed-name` | No | `""` | Human-readable feed name, included in output metadata |

### Examples

**Download today's entries from arXiv AI feed:**

```bash
python download_feed.py \
  --url "http://rss.arxiv.org/rss/cs.AI" \
  --output /tmp/feeds/arxiv-ai \
  --cutoff 24 \
  --feed-id arxiv-ai \
  --feed-name "arXiv AI"
```

**Download all entries (no cutoff):**

```bash
python download_feed.py \
  --url "https://cacm.acm.org/feed/" \
  --output /tmp/feeds/acm-cacm \
  --cutoff 0 \
  --feed-id acm-cacm
```

**Minimal usage (feed-id derived from URL):**

```bash
python download_feed.py \
  --url "http://rss.arxiv.org/rss/cs.AI" \
  --output /tmp/feeds/output
```

## Output Format

The script writes one Markdown file per entry to the output directory.

**File naming:** `{sanitized-entry-id}.md`

**Entry ID generation:**
- Use `<guid>` (RSS) or `<id>` (Atom) if present
- Fallback: SHA-256 hash of `<link>` truncated to 12 characters
- Sanitized for filesystem: non-alphanumeric chars → `-`, lowercase

**Markdown structure:**

```markdown
---
feed_id: arxiv-ai
feed_name: "arXiv Computer Science - Artificial Intelligence"
entry_id: "2602.12345v1"
title: "Paper Title Here"
link: "https://arxiv.org/abs/2602.12345v1"
date: "2026-02-12T08:00:00+00:00"
authors: "Author One, Author Two"
---

Description or abstract content here, plain text, HTML stripped.
```

The YAML frontmatter makes each file machine-readable. The body contains the description/abstract with HTML tags stripped and entities decoded.

## Behavior

### Feed Format Detection

The script auto-detects:
- **RSS 2.0**: Root tag `<rss>`
- **Atom**: Root tag `<feed xmlns="...atom...">` or any tag containing "atom"

### Date Parsing

Supports multiple date formats:
- RFC 2822: `Mon, 12 Feb 2026 08:00:00 +0000`
- ISO 8601: `2026-02-12T08:00:00+00:00`
- ISO 8601 UTC: `2026-02-12T08:00:00Z`
- Simple date: `2026-02-12`

All dates are normalized to ISO 8601 UTC format in the output.

### Cutoff Filtering

Entries are filtered based on their publication date (`pubDate` in RSS, `updated` or `published` in Atom):

- **Entries with dates**: Included if published within `--cutoff` hours from now
- **Entries without dates**: Included (fail open)
- **Cutoff = 0**: All entries included

This ensures new entries are never accidentally excluded due to missing metadata.

### HTML Handling

- **HTML tags**: Stripped from descriptions using regex
- **HTML entities**: Decoded (`&amp;` → `&`, `&lt;` → `<`, etc.)
- **Excessive whitespace**: Collapsed to single spaces

### Error Handling

| Error Type | Behavior |
|------------|----------|
| HTTP errors (4xx, 5xx) | Print error to stderr, exit 1 |
| Network timeout (>30s) | Print error to stderr, exit 1 |
| Malformed XML | Print error to stderr, exit 1 |
| Individual entry parse failures | Log warning to stderr, skip entry, continue |
| Unknown feed format | Print error to stderr, exit 1 |

**Success:** Exit 0 even if 0 entries written (e.g., all entries older than cutoff)

### Output Summary

The script prints a JSON summary to stdout on success:

```json
{
  "feed_id": "arxiv-ai",
  "entries_found": 50,
  "entries_written": 12,
  "entries_skipped_cutoff": 38
}
```

This allows the calling workflow to track processing statistics.

## Integration with Workflow

This script is called by `.github/workflows/daily-research-monitor.yml`:

```yaml
- name: Download RSS feeds
  run: |
    mkdir -p /tmp/research-monitor/feeds
    
    python3 -c "
    import yaml, subprocess, sys, json
    
    with open('workspace/feeds.yml') as f:
        feeds = yaml.safe_load(f)['feeds']
    
    results = []
    
    for feed in feeds:
        print(f\"📡 Downloading feed '{feed['id']}': {feed['url']}\")
        output_dir = f\"/tmp/research-monitor/feeds/{feed['id']}\"
        
        result = subprocess.run([
            sys.executable, 'system/src/feed-downloader/download_feed.py',
            '--url', feed['url'],
            '--output', output_dir,
            '--cutoff', '24',
            '--feed-id', feed['id'],
            '--feed-name', feed.get('name', '')
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f\"⚠️  Feed '{feed['id']}' failed: {result.stderr.strip()}\")
        else:
            print(f\"✅ {result.stdout.strip()}\")
            results.append(json.loads(result.stdout.strip()))
    
    total = sum(r.get('entries_written', 0) for r in results)
    print(f\"\\n📊 Total entries downloaded: {total} from {len(results)} feeds\")
    "
```

The workflow then points the Copilot CLI agent to `/tmp/research-monitor/feeds/` to read the pre-structured content.

## Design Decisions

- **One feed at a time**: The script processes a single `--url`. The workflow orchestrates multiple feeds.
- **One Markdown file per entry**: Enables selective reading and human inspection.
- **YAML frontmatter**: Follows repository convention (same as ideas, bibliography, etc.).
- **Cutoff default 24h**: Matches daily schedule. Override as needed (e.g., `72` for Monday runs).
- **Fail open on missing dates**: Better to include an undated entry than exclude it incorrectly.
- **No deduplication**: Cross-feed dedup (if needed) is the agent's job during filtering.
- **Stdlib XML parser**: Uses `xml.etree.ElementTree` (no lxml needed) for simplicity.

## Troubleshooting

### Network Errors

If feeds fail to download:
- Check URL is correct and accessible
- Verify network connectivity
- Check for rate limiting or blocked User-Agents

### Parse Errors

If XML parsing fails:
- Verify the feed URL returns valid RSS/Atom XML
- Check for server-side errors (5xx responses)
- Try fetching the URL manually with `curl` to inspect the response

### Missing Entries

If expected entries are missing:
- Check cutoff parameter (use `--cutoff 0` to disable)
- Verify entry dates are within the cutoff window
- Look for parse warnings in stderr

### File Naming Collisions

Entry IDs are generated from `guid`/`id` fields or link hashes. Collisions are extremely rare but possible. If detected, check for duplicate entries in the feed.

## Technical Details

- **HTTP library**: `requests` (with proper User-Agent and Accept headers)
- **XML parser**: `xml.etree.ElementTree` (Python stdlib)
- **YAML**: `pyyaml` (used by workflow orchestration, not the script itself)
- **Python version**: Python 3.7+

## License

This tool is part of the talk-to-my-agent repository.
