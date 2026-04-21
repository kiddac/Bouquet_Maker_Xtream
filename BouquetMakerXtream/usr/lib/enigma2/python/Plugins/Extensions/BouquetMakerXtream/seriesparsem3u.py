#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
from . import bouquet_globals as glob
from .plugin import debugs

# Strict patterns
SERIES_PATTERN = re.compile(r'\bS\d{1,4}\b', re.IGNORECASE)
EPISODE_PATTERN = re.compile(r'\bE\d{1,4}\b', re.IGNORECASE)
EPISODE_WORD_PATTERN = re.compile(r'\bEpisode\s\d+\b', re.IGNORECASE)


def is_series_stream(name, lower_source):
    """
    Strict detection:
    - Accept if URL explicitly contains /series/
    - OR name contains BOTH season + episode
    """
    if "/series/" in lower_source:
        return True

    has_season = SERIES_PATTERN.search(name)
    has_episode = EPISODE_PATTERN.search(name) or EPISODE_WORD_PATTERN.search(name)

    return bool(has_season and has_episode)


# --------------------------------------------------
# FULL PLAYLIST PARSER (non-streaming)
# --------------------------------------------------

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
    pending_url = None

    while i < total_lines:
        line = lines[i].strip()
        i += 1

        if not line:
            continue

        # URL BEFORE EXTINF (edge case)
        if line.startswith(('http://', 'https://')):
            pending_url = line.split()[0]
            continue

        if not line.startswith('#EXTINF'):
            pending_url = None
            continue

        extinf_line = line

        # get URL
        if pending_url:
            source = pending_url
            pending_url = None
        else:
            if i >= total_lines:
                break
            url_line = lines[i].strip()
            i += 1

            if not url_line.startswith(('http://', 'https://')):
                continue

            source = url_line.split()[0]

        lower_source = source.lower()

        # reject obvious non-series paths
        if "/live/" in lower_source or "/movie" in lower_source:
            continue

        # group-title
        group_title = ""
        gt_pos = extinf_line.find('group-title="')
        if gt_pos > -1:
            end_pos = extinf_line.find('"', gt_pos + 13)
            if end_pos > -1:
                group_title = extinf_line[gt_pos + 13:end_pos].strip()

        # skip hidden categories (BY NAME)
        if group_title and group_title in hidden_categories:
            continue

        # name extraction
        name = ""
        name_pos = extinf_line.find('tvg-name="')
        if name_pos > -1:
            end_pos = extinf_line.find('"', name_pos + 10)
            if end_pos > -1:
                name = extinf_line[name_pos + 10:end_pos].strip()

        if not name:
            last_comma = extinf_line.rfind(',')
            if last_comma > -1:
                name = extinf_line[last_comma + 1:].strip()

        if not name:
            continue

        # strict detection
        if not is_series_stream(name, lower_source):
            continue

        streamid += 1

        series_streams.append({
            "category_id": group_title or "Uncategorised Series",
            "name": simplify_name(name),
            "source": source,
            "series_id": str(streamid)
        })

    return series_streams


# --------------------------------------------------
# STREAMING PARSER (memory-safe)
# --------------------------------------------------

def parseM3u8Stream(lines):
    data = glob.current_playlist["data"]
    hidden_categories = set(data.get("series_categories_hidden", []))

    current = {}
    pending_url = None

    for line in lines:

        if isinstance(line, bytes):
            try:
                line = line.decode("utf-8", "ignore")
            except:
                continue

        line = line.strip()

        if not line:
            continue

        # URL handling
        if line.startswith(('http://', 'https://')):

            if current:
                source = line.split()[0]
                lower_source = source.lower()
                name = current.get("name", "")

                if "/live/" in lower_source or "/movie" in lower_source:
                    current = {}
                    continue

                if not is_series_stream(name, lower_source):
                    current = {}
                    continue

                current["source"] = source
                yield current
                current = {}

            else:
                pending_url = line.split()[0]

            continue

        # non EXTINF
        if not line.startswith('#EXTINF'):
            if not line.startswith('#'):
                pending_url = None
                current = {}
            continue

        # parse EXTINF
        name = ""
        group = ""

        try:
            if ',' in line:
                name = line.split(',', 1)[1].strip()

            if 'group-title="' in line:
                group = line.split('group-title="', 1)[1].split('"', 1)[0].strip()
        except:
            pass

        # skip hidden categories
        if group and group in hidden_categories:
            pending_url = None
            current = {}
            continue

        current = {
            "name": simplify_name(name),
            "category_id": group or "Uncategorised Series",
            "added": "0"
        }

        # handle URL before EXTINF
        if pending_url:
            source = pending_url
            pending_url = None

            lower_source = source.lower()
            name = current.get("name", "")

            if "/live/" in lower_source or "/movie" in lower_source:
                current = {}
                continue

            if not is_series_stream(name, lower_source):
                current = {}
                continue

            current["source"] = source
            yield current
            current = {}


# --------------------------------------------------
# NAME CLEANUP
# --------------------------------------------------

def simplify_name(input_string):
    if not input_string:
        return input_string

    try:
        cleaned = input_string.replace(':', '').replace('"', '').strip('- ')
        cleaned = ' '.join(cleaned.split())

        parts = cleaned.split(' - ')
        if len(parts) > 1 and parts[0] in parts[1]:
            return ' - '.join([parts[0]] + parts[2:])
        elif len(parts) > 2 and parts[0] in parts[2]:
            return ' - '.join([parts[0], parts[1]] + parts[3:])

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
