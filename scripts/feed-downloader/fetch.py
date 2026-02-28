#!/usr/bin/env python3
"""
RSS/Atom Feed Downloader

Downloads all feeds defined in a YAML config file and outputs one
Markdown file per entry, organised into per-feed subdirectories.
Part of the deterministic phase in the daily RSS monitor workflow.

Usage:
    python fetch.py \\
      --config conf/feeds.yml \\
      --output /tmp/rss-monitor/feeds \\
      --cutoff 24

The config file must contain a top-level ``feeds`` list, e.g.::

    feeds:
      - id: arxiv-ai
        name: "arXiv CS.AI"
        url: "http://rss.arxiv.org/rss/cs.AI"
        update_frequency: daily   # or "weekly"

Weekly feeds are only fetched on Fridays (day-of-week == 5) unless
``--ignore-schedule`` is passed.

Output structure::

    <output>/
      <feed-id>/
        <entry-id>.md
        titles.jsonl
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List

import requests
import yaml


def sanitize_filename(text: str) -> str:
    """
    Sanitize text for use as a filename.
    Replace non-alphanumeric characters with hyphens, lowercase.
    """
    # Replace non-alphanumeric with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Lowercase
    sanitized = sanitized.lower()
    return sanitized


def generate_entry_id(guid: Optional[str], link: str) -> str:
    """
    Generate a unique entry ID from guid or link.
    
    Args:
        guid: The entry's guid or id field (if present)
        link: The entry's link URL
        
    Returns:
        Sanitized entry ID suitable for use as a filename
    """
    if guid:
        # Use guid if available
        entry_id = sanitize_filename(guid)
    else:
        # Fallback: SHA-256 hash of link (truncated to 12 chars)
        hash_obj = hashlib.sha256(link.encode('utf-8'))
        entry_id = hash_obj.hexdigest()[:12]
    
    return entry_id


def strip_html_tags(text: str) -> str:
    """
    Strip HTML tags from text and decode HTML entities.
    
    Args:
        text: Text potentially containing HTML
        
    Returns:
        Plain text with tags removed and entities decoded
    """
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Replace common block-level tags with spaces to preserve word boundaries
    text = re.sub(r'</(p|div|br|h[1-6]|li|tr|td)>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<(br|hr)\s*/?>', ' ', text, flags=re.IGNORECASE)
    
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse various date formats to ISO 8601 format.
    
    Args:
        date_str: Date string in various formats (RFC 2822, ISO 8601, etc.)
        
    Returns:
        ISO 8601 formatted date string, or None if parsing fails
    """
    if not date_str:
        return None
    
    # Try common date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822: "Mon, 12 Feb 2026 08:00:00 +0000"
        "%Y-%m-%dT%H:%M:%S%z",        # ISO 8601: "2026-02-12T08:00:00+00:00"
        "%Y-%m-%dT%H:%M:%SZ",         # ISO 8601 UTC: "2026-02-12T08:00:00Z"
        "%Y-%m-%d",                   # Simple date: "2026-02-12"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            # Convert to UTC if timezone-aware
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc)
            else:
                # Assume UTC if no timezone info
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    
    # If all parsing attempts fail, return None
    return None


def parse_rss_entry(item: ET.Element) -> Optional[Dict[str, str]]:
    """
    Parse an RSS 2.0 <item> element.
    
    Args:
        item: XML element representing an RSS item
        
    Returns:
        Dictionary with entry fields, or None on parse failure
    """
    try:
        # Extract fields with namespace handling
        title_elem = item.find('title')
        link_elem = item.find('link')
        desc_elem = item.find('description')
        date_elem = item.find('pubDate')
        guid_elem = item.find('guid')
        
        # Author can be in multiple places
        author_elem = item.find('author')
        if author_elem is None:
            # Try Dublin Core namespace
            author_elem = item.find('{http://purl.org/dc/elements/1.1/}creator')
        
        title = title_elem.text if title_elem is not None else ""
        link = link_elem.text if link_elem is not None else ""
        description = desc_elem.text if desc_elem is not None else ""
        pub_date = date_elem.text if date_elem is not None else None
        guid = guid_elem.text if guid_elem is not None else None
        author = author_elem.text if author_elem is not None else ""
        
        # Link is required
        if not link:
            return None
        
        return {
            'title': title.strip() if title else "",
            'link': link.strip(),
            'description': strip_html_tags(description),
            'date': parse_date(pub_date),
            'guid': guid.strip() if guid else None,
            'authors': author.strip() if author else "",
        }
    except Exception as e:
        print(f"Warning: Failed to parse RSS entry: {e}", file=sys.stderr)
        return None


def parse_atom_entry(entry: ET.Element, ns: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Parse an Atom <entry> element.
    
    Args:
        entry: XML element representing an Atom entry
        ns: Namespace dictionary
        
    Returns:
        Dictionary with entry fields, or None on parse failure
    """
    try:
        # Extract fields
        title_elem = entry.find('atom:title', ns)
        link_elem = entry.find("atom:link[@rel='alternate']", ns)
        if link_elem is None:
            # Fallback to first link without rel attribute
            link_elem = entry.find('atom:link', ns)
        summary_elem = entry.find('atom:summary', ns)
        if summary_elem is None:
            summary_elem = entry.find('atom:content', ns)
        date_elem = entry.find('atom:updated', ns)
        if date_elem is None:
            date_elem = entry.find('atom:published', ns)
        id_elem = entry.find('atom:id', ns)
        
        # Authors can be multiple
        author_elems = entry.findall('atom:author/atom:name', ns)
        authors = ", ".join([a.text for a in author_elems if a.text])
        
        title = title_elem.text if title_elem is not None else ""
        link = link_elem.get('href', '') if link_elem is not None else ""
        summary = summary_elem.text if summary_elem is not None else ""
        date = date_elem.text if date_elem is not None else None
        entry_id = id_elem.text if id_elem is not None else None
        
        # Link is required
        if not link:
            return None
        
        return {
            'title': title.strip() if title else "",
            'link': link.strip(),
            'description': strip_html_tags(summary),
            'date': parse_date(date),
            'guid': entry_id.strip() if entry_id else None,
            'authors': authors,
        }
    except Exception as e:
        print(f"Warning: Failed to parse Atom entry: {e}", file=sys.stderr)
        return None


def is_within_cutoff(entry_date: Optional[str], cutoff_hours: int) -> bool:
    """
    Check if an entry date is within the cutoff period.
    
    Args:
        entry_date: ISO 8601 date string
        cutoff_hours: Hours to look back (0 = no cutoff)
        
    Returns:
        True if within cutoff or no date present (fail open), False otherwise
    """
    if cutoff_hours == 0:
        return True
    
    if not entry_date:
        # Fail open: include entries without dates
        return True
    
    try:
        entry_dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=cutoff_hours)
        return entry_dt >= cutoff_dt
    except Exception:
        # Parse failure: fail open
        return True


def write_entry_markdown(entry: Dict[str, str], output_dir: Path, feed_id: str, feed_name: str) -> Optional[Dict[str, str]]:
    """
    Write an entry to a Markdown file with YAML frontmatter.
    
    Args:
        entry: Entry data dictionary
        output_dir: Output directory path
        feed_id: Feed identifier
        feed_name: Human-readable feed name
        
    Returns:
        Entry metadata dict on success (for titles.jsonl), None on failure
    """
    try:
        # Generate entry ID and filename
        entry_id = generate_entry_id(entry['guid'], entry['link'])
        filename = f"{entry_id}.md"
        filepath = output_dir / filename
        
        # Format YAML frontmatter
        frontmatter = f"""---
feed_id: {feed_id}
feed_name: "{feed_name}"
entry_id: "{entry_id}"
title: "{entry['title'].replace('"', '\\"')}"
link: "{entry['link']}"
date: "{entry['date'] or ''}"
authors: "{entry['authors'].replace('"', '\\"')}"
---

{entry['description']}
"""
        
        # Write file
        filepath.write_text(frontmatter, encoding='utf-8')
        return {
            'entry_id': entry_id,
            'title': entry['title'],
            'link': entry['link'],
            'date': entry['date'] or '',
            'authors': entry['authors'],
            'feed_id': feed_id,
        }
    except Exception as e:
        print(f"Warning: Failed to write entry {entry.get('link', 'unknown')}: {e}", file=sys.stderr)
        return None


def write_titles_jsonl(entries: List[Dict[str, str]], output_dir: Path) -> None:
    """
    Write a titles.jsonl file containing one JSON object per entry.
    
    This file enables lightweight first-pass title-based filtering
    without needing to read individual entry Markdown files.
    
    Args:
        entries: List of entry metadata dicts
        output_dir: Output directory path
    """
    filepath = output_dir / 'titles.jsonl'
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Warning: Failed to write titles.jsonl: {e}", file=sys.stderr)


def download_feed(url: str, output_dir: str, cutoff: int, feed_id: str, feed_name: str) -> Dict[str, int]:
    """
    Download and parse a single feed, writing entries to Markdown files.

    Args:
        url: RSS or Atom feed URL
        output_dir: Output directory path (entries are written here directly)
        cutoff: Hours to look back (0 = no cutoff)
        feed_id: Feed identifier
        feed_name: Human-readable feed name

    Returns:
        Dictionary with counts: feed_id, entries_found, entries_written,
        entries_skipped_cutoff

    Raises:
        RuntimeError: on network or parse failures (caller decides policy)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Fetch feed with proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml,application/xml,text/xml,*/*;q=0.8',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch feed from {url}: {e}") from e

    # Parse XML
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse XML from {url}: {e}") from e

    # Detect format and parse entries
    entries: List[Dict[str, str]] = []

    if root.tag == 'rss':
        # RSS 2.0 format
        for item in root.findall('.//item'):
            entry = parse_rss_entry(item)
            if entry:
                entries.append(entry)
    elif root.tag.endswith('feed') or 'atom' in root.tag.lower():
        # Atom format
        ns_match = re.search(r'\{([^}]+)\}', root.tag)
        ns = {'atom': ns_match.group(1)} if ns_match else {
            'atom': 'http://www.w3.org/2005/Atom'}

        for entry_elem in root.findall('atom:entry', ns):
            entry = parse_atom_entry(entry_elem, ns)
            if entry:
                entries.append(entry)
    else:
        raise RuntimeError(f"Unknown feed format (root tag: {root.tag})")

    # Apply cutoff filter and write entries
    entries_written = 0
    entries_skipped = 0
    written_entries: List[Dict[str, str]] = []

    for entry in entries:
        if is_within_cutoff(entry['date'], cutoff):
            result = write_entry_markdown(entry, output_path, feed_id, feed_name)
            if result:
                entries_written += 1
                written_entries.append(result)
        else:
            entries_skipped += 1

    # Write titles.jsonl for lightweight first-pass filtering
    if written_entries:
        write_titles_jsonl(written_entries, output_path)

    return {
        'feed_id': feed_id,
        'entries_found': len(entries),
        'entries_written': entries_written,
        'entries_skipped_cutoff': entries_skipped,
    }


def download_all_feeds(
    config_path: str,
    output_dir: str,
    cutoff: int,
    ignore_schedule: bool = False,
) -> Dict:
    """
    Read a feeds YAML config and download every applicable feed.

    Args:
        config_path: Path to the feeds.yml config file
        output_dir: Root output directory; each feed gets a subdirectory
        cutoff: Hours to look back (0 = no cutoff)
        ignore_schedule: If True, download weekly feeds regardless of day

    Returns:
        Summary dictionary with per-feed results and totals
    """
    config = Path(config_path)
    if not config.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    feeds = data.get('feeds', [])
    if not feeds:
        print("Warning: No feeds defined in config", file=sys.stderr)

    day_of_week = datetime.now(timezone.utc).isoweekday()  # 1=Mon … 7=Sun

    results: List[Dict] = []
    skipped: List[str] = []
    failed: List[Dict[str, str]] = []

    for feed in feeds:
        feed_id = feed.get('id', '')
        feed_name = feed.get('name', '')
        url = feed.get('url', '')
        freq = feed.get('update_frequency', 'daily')

        if not url:
            print(f"Warning: Feed '{feed_id}' has no URL — skipping",
                  file=sys.stderr)
            continue

        # Schedule check: weekly feeds only on Fridays (day 5)
        if not ignore_schedule and freq == 'weekly' and day_of_week != 5:
            print(f"⏭️  Skipping weekly feed '{feed_id}' (not Friday)")
            skipped.append(feed_id)
            continue

        feed_output = str(Path(output_dir) / feed_id)
        print(f"📡 Downloading feed '{feed_id}': {url}")

        try:
            result = download_feed(url, feed_output, cutoff, feed_id, feed_name)
            print(f"✅ {feed_id}: {result['entries_written']} entries written "
                  f"({result['entries_skipped_cutoff']} outside cutoff)")
            results.append(result)
        except RuntimeError as exc:
            print(f"⚠️  Feed '{feed_id}' failed: {exc}", file=sys.stderr)
            failed.append({'feed_id': feed_id, 'error': str(exc)})

    total_written = sum(r.get('entries_written', 0) for r in results)
    print(f"\n📊 Total entries downloaded: {total_written} "
          f"from {len(results)} feeds "
          f"({len(skipped)} skipped, {len(failed)} failed)")

    return {
        'feeds_processed': len(results),
        'feeds_skipped': len(skipped),
        'feeds_failed': len(failed),
        'total_entries_written': total_written,
        'results': results,
        'skipped': skipped,
        'failed': failed,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Download RSS/Atom feeds defined in a YAML config'
    )
    parser.add_argument(
        '--config', required=True,
        help='Path to feeds YAML config (e.g. conf/feeds.yml)',
    )
    parser.add_argument(
        '--output', required=True,
        help='Root output directory (per-feed subdirs created automatically)',
    )
    parser.add_argument(
        '--cutoff', type=int, default=24,
        help='Hours to look back (0 = no cutoff, default: 24)',
    )
    parser.add_argument(
        '--ignore-schedule', action='store_true', default=False,
        help='Download weekly feeds regardless of day of week',
    )

    args = parser.parse_args()

    summary = download_all_feeds(
        config_path=args.config,
        output_dir=args.output,
        cutoff=args.cutoff,
        ignore_schedule=args.ignore_schedule,
    )

    # Print JSON summary to stdout
    print(json.dumps(summary))
    sys.exit(0)


if __name__ == '__main__':
    main()
