#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from . import bouquet_globals as glob
from .plugin import debugs

# Keep only essential regex patterns
GROUP_TITLE_RE = re.compile(r'group-title="([^"]*)"')
TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')
SERIES_PATTERN = re.compile(r'(?i)(S\d+|E\d+|Episode\s\d+)')  # Case-insensitive matching


def parseM3u8Playlist(response):
    if debugs:
        print("*** parseM3u8Playlist ***")

    data = glob.current_playlist["data"]
    data["series_streams"] = []
    streamid = 0

    if isinstance(response, bytes):
        response = response.decode('utf-8', 'ignore')

    lines = response.splitlines()
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i].strip()
        i += 1

        if not line.startswith("#EXTINF"):
            continue

        # Process EXTINF line
        group_title = ""
        name = ""

        # Extract group-title (optimized)
        gt_pos = line.find('group-title="')
        if gt_pos > -1:
            end_pos = line.find('"', gt_pos + 13)
            if end_pos > -1:
                group_title = line[gt_pos + 13:end_pos].strip()

        # Skip hidden categories early
        if group_title and isinstance(data.get("series_categories_hidden", []), list) \
           and group_title in data["series_categories_hidden"]:
            continue

        # Extract name (optimized)
        name_pos = line.find('tvg-name="')
        if name_pos > -1:
            end_pos = line.find('"', name_pos + 10)
            if end_pos > -1:
                name = line[name_pos + 10:end_pos].strip()

        # Fallback to name after last comma (without regex)
        if not name:
            last_comma = line.rfind(',')
            if last_comma > -1:
                name = line[last_comma + 1:].strip()

        name = simplify_name(name)

        if not name:
            continue

        # Get the URL line
        if i >= total_lines:
            break

        url_line = lines[i].strip()
        i += 1

        # Fast URL check (replaces URL_PATTERN regex)
        if not url_line.startswith(('http://', 'https://')):
            continue

        source = url_line.split()[0]  # Take first token as URL

        # Series detection
        is_series = (
            "/series/" in source.lower() or
            SERIES_PATTERN.search(name)
        )

        if is_series:
            streamid += 1
            data["series_streams"].append({
                "category_id": group_title or "Uncategorised Series",
                "name": name,
                "source": source,
                "series_id": str(streamid),
                "added": 0
            })


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
