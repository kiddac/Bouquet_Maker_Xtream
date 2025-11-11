#!/usr/bin/python
# -*- coding: utf-8 -*-
# import io
# import gc
import re
from . import bouquet_globals as glob
from .plugin import debugs

SERIES_PATTERN = re.compile(r'(S\d+|E\d+|Episode\s\d+)', re.IGNORECASE)


def parseM3u8Playlist_streaming(pipe_process):
    """
    Stream-parse M3U8 directly from curl pipe process.
    Never loads full file into memory.

    Args:
        pipe_process: subprocess.Popen object or file-like object with stdout
    """
    data = glob.current_playlist["data"]
    series_streams = []
    streamid = 0
    hidden_categories = set(data.get("series_categories_hidden", []))

    # Stream lines directly from curl stdout
    line_iter = iter(pipe_process.stdout.readline, b'')
    pending_extinf = None

    for raw_line in line_iter:
        try:
            line = raw_line.decode('utf-8', 'ignore').strip()
        except Exception:
            continue

        if not line:
            continue

        # Handle EXTINF lines
        if line.startswith("#EXTINF"):
            pending_extinf = line
            continue

        # Process URL line if we have a pending EXTINF
        if pending_extinf and line.startswith(('http://', 'https://')):
            process_entry(pending_extinf, line, hidden_categories, series_streams, streamid)
            if series_streams and len(series_streams) > streamid:
                streamid = len(series_streams)
            pending_extinf = None

    return series_streams


def process_entry(extinf_line, url_line, hidden_categories, series_streams, streamid):
    """Process a single EXTINF + URL pair"""

    # Extract group-title
    group_title = ""
    gt_pos = extinf_line.find('group-title="')
    if gt_pos > -1:
        end_pos = extinf_line.find('"', gt_pos + 13)
        if end_pos > -1:
            group_title = extinf_line[gt_pos + 13:end_pos].strip()

    # Skip hidden categories
    if group_title and group_title in hidden_categories:
        return

    # Extract name
    name = ""
    name_pos = extinf_line.find('tvg-name="')
    if name_pos > -1:
        end_pos = extinf_line.find('"', name_pos + 10)
        if end_pos > -1:
            name = extinf_line[name_pos + 10:end_pos].strip()

    # Fallback to name after last comma
    if not name:
        last_comma = extinf_line.rfind(',')
        if last_comma > -1:
            name = extinf_line[last_comma + 1:].strip()

    if not name:
        return

    source = url_line.split()[0]

    # Early rejection of non-series paths
    lower_source = source.lower()
    if "/live/" in lower_source or "/movies/" in lower_source:
        return

    # Series detection
    is_series = (
        "/series/" in lower_source or
        SERIES_PATTERN.search(name)
    )

    if is_series:
        series_streams.append({
            "category_id": group_title or "Uncategorised Series",
            "name": simplify_name(name),
            "source": source,
            "series_id": str(len(series_streams) + 1)
        })


def parseM3u8Playlist(response):
    data = glob.current_playlist["data"]
    series_streams = []
    streamid = 0

    if isinstance(response, bytes):
        response = response.decode('utf-8', 'ignore')

    lines = response.splitlines()
    total_lines = len(lines)
    hidden_categories = set(data.get("series_categories_hidden", []))

    i = 0
    while i < total_lines:
        line = lines[i].strip()
        i += 1

        if not line.startswith("#EXTINF"):
            continue

        # Extract group-title early using string methods (faster than regex)
        group_title = ""
        gt_pos = line.find('group-title="')
        if gt_pos > -1:
            end_pos = line.find('"', gt_pos + 13)
            if end_pos > -1:
                group_title = line[gt_pos + 13:end_pos].strip()

        # Skip hidden categories immediately (optimization from second file)
        if group_title and group_title in hidden_categories:
            # Skip URL line and continue
            if i < total_lines:
                i += 1
            continue

        # Extract name using string methods (faster than regex)
        name = ""
        name_pos = line.find('tvg-name="')
        if name_pos > -1:
            end_pos = line.find('"', name_pos + 10)
            if end_pos > -1:
                name = line[name_pos + 10:end_pos].strip()

        # Fallback to name after last comma
        if not name:
            last_comma = line.rfind(',')
            if last_comma > -1:
                name = line[last_comma + 1:].strip()

        if not name:
            # Skip URL line and continue
            if i < total_lines:
                i += 1
            continue

        # Get URL line
        if i >= total_lines:
            break

        url_line = lines[i].strip()
        i += 1

        # Validate URL
        if not url_line.startswith(('http://', 'https://')):
            continue

        source = url_line.split()[0]  # Take first token as URL

        # Early rejection of non-series paths (from first file - good filtering)
        lower_source = source.lower()
        if "/live/" in lower_source or "/movies/" in lower_source:
            continue

        # Series detection (combined logic)
        is_series = (
            "/series/" in lower_source or
            SERIES_PATTERN.search(name)
        )

        if is_series:
            streamid += 1
            series_streams.append({
                "category_id": group_title or "Uncategorised Series",
                "name": simplify_name(name),
                "source": source,
                "series_id": str(streamid)
            })

    return series_streams


def simplify_name(input_string):
    if not input_string:
        return input_string

    try:
        # Fast initial cleaning
        cleaned = input_string.replace(':', '').replace('"', '').strip('- ')
        cleaned = ' '.join(cleaned.split())  # Faster than re.sub for spaces

        # Fast duplicate detection for common TV title patterns
        parts = cleaned.split(' - ')
        if len(parts) > 1 and parts[0] in parts[1]:
            # Case: "Show Name S01 - Show Name - S01E01 - Episode"
            return ' - '.join([parts[0]] + parts[2:])
        elif len(parts) > 2 and parts[0] in parts[2]:
            # Case: "Show Name (2020) S01 - Show Name - S01E01"
            return ' - '.join([parts[0], parts[1]] + parts[3:])

        # Fallback for other patterns
        words = cleaned.split()
        unique_words = []
        seen = set()
        for word in words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)
        return ' '.join(unique_words)

    except Exception as e:
        if debugs:
            print("Name cleaning error for '%s': %s" % (input_string, str(e)))
        return input_string
