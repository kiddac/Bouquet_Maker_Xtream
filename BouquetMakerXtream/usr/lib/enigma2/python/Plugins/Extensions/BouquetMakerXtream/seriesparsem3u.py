#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from . import bouquet_globals as glob
from .plugin import debugs

GROUP_TITLE_RE = re.compile(r'group-title="([^"]*)"')
TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')
SERIES_PATTERN = re.compile(r'(S\d+|E\d+|Episode\s\d+)', re.IGNORECASE)


def parseM3u8Playlist(response):
    if debugs:
        print("*** parseM3u8Playlist ***")

    data = glob.current_playlist["data"]
    data["series_streams"] = []
    streamid = 0

    if isinstance(response, bytes):
        response = response.decode('utf-8', 'ignore')

    lines = response.splitlines()
    total_lines = len(lines)
    hidden = set(data.get("series_categories_hidden", []))

    i = 0
    while i < total_lines:
        line = lines[i]
        i += 1

        if not line.startswith("#EXTINF"):
            continue

        # Get URL first (next line)
        if i >= total_lines:
            break
        url_line = lines[i].strip()
        i += 1

        if not url_line.startswith(('http://', 'https://')):
            continue

        source = url_line.split()[0]

        # Early rejection of non-series paths
        lower_source = source.lower()
        if "/live/" in lower_source or "/movies/" in lower_source:
            continue

        # Quick series check: URL contains '/series/'? If not, fallback to name regex
        is_series_url = "/series/" in lower_source

        # Extract tvg-name
        m_name = TVG_NAME_RE.search(line)
        name = m_name.group(1).strip() if m_name else ""
        if not name:
            last_comma = line.rfind(',')
            if last_comma > -1:
                name = line[last_comma + 1:].strip()

        if not name:
            continue

        # Series check: URL or name pattern
        if not (is_series_url or SERIES_PATTERN.search(name)):
            continue

        # Extract group-title last (skip hidden categories check if possible)
        m_group = GROUP_TITLE_RE.search(line)
        group_title = m_group.group(1).strip() if m_group else ""
        if group_title and group_title in hidden:
            continue

        # Append series
        streamid += 1
        data["series_streams"].append({
            "category_id": group_title or "Uncategorised Series",
            "name": simplify_name(name),
            "source": source,
            "series_id": str(streamid),
        })
    return data["series_streams"]


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
