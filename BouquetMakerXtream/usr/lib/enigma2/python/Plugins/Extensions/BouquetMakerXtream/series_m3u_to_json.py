#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import re
import gc
from . import bouquet_globals as glob
from .plugin import debugs

# ✅ Strict patterns (same as other parsers)
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


def convert_m3u_to_json(m3u_path, json_path):
    if debugs:
        print("*** convert_m3u_to_json ***")

    data = glob.current_playlist.get("data") or {}
    hidden_categories = set(data.get("series_categories_hidden") or [])

    streamid = 0
    first = True

    try:
        with open(m3u_path, 'r') as infile, open(json_path, 'w') as outfile:
            outfile.write('[')

            current = {}
            pending_url = None  # handle URL-before-EXTINF case

            for raw_line in infile:
                line = (raw_line or "").strip()

                if not line:
                    continue

                # URL before EXTINF
                if line.startswith(('http://', 'https://')):
                    if current:
                        source = line.split()[0]
                        lower_source = source.lower()
                        name = current.get("name") or ""

                        # reject non-series paths
                        if "/live/" in lower_source or "/movie" in lower_source:
                            current = {}
                            continue

                        # strict detection
                        if not is_series_stream(name, lower_source):
                            current = {}
                            continue

                        streamid += 1
                        current["source"] = source
                        current["series_id"] = str(streamid)

                        if not first:
                            outfile.write(',')
                        json.dump(current, outfile)
                        first = False

                        current = {}
                    else:
                        pending_url = line.split()[0]

                    continue

                # non EXTINF
                if not line.startswith('#EXTINF'):
                    if not line.startswith('#'):
                        current = {}
                        pending_url = None
                    continue

                # parse EXTINF
                group_title = ""
                name = ""

                gt_pos = line.find('group-title="')
                if gt_pos > -1:
                    end_pos = line.find('"', gt_pos + 13)
                    if end_pos > -1:
                        group_title = (line[gt_pos + 13:end_pos] or "").strip()

                # skip hidden categories (BY NAME)
                if group_title and group_title in hidden_categories:
                    current = {}
                    pending_url = None
                    continue

                name_pos = line.find('tvg-name="')
                if name_pos > -1:
                    end_pos = line.find('"', name_pos + 10)
                    if end_pos > -1:
                        name = (line[name_pos + 10:end_pos] or "").strip()

                if not name:
                    last_comma = line.rfind(',')
                    if last_comma > -1:
                        name = (line[last_comma + 1:] or "").strip()

                current = {
                    "category_id": group_title or "Uncategorised Series",
                    "name": simplify_name(name)
                }

                # handle URL already seen before EXTINF
                if pending_url:
                    source = pending_url
                    pending_url = None

                    lower_source = source.lower()
                    name = current.get("name") or ""

                    if "/live/" in lower_source or "/movie" in lower_source:
                        current = {}
                        continue

                    if not is_series_stream(name, lower_source):
                        current = {}
                        continue

                    streamid += 1
                    current["source"] = source
                    current["series_id"] = str(streamid)

                    if not first:
                        outfile.write(',')
                    json.dump(current, outfile)
                    first = False

                    current = {}

            outfile.write(']')

    except Exception as e:
        print("Error converting m3u: %s" % str(e))

    finally:
        try:
            del current, line, raw_line
        except:
            pass
        gc.collect()


def simplify_name(name):
    if not name:
        return ""

    try:
        cleaned = (name or "").replace(':', '').replace('"', '').strip('- ')
        cleaned = ' '.join(cleaned.split())
        return cleaned

    except Exception as e:
        if debugs:
            print("simplify_name error: %s" % str(e))
        return name or ""
