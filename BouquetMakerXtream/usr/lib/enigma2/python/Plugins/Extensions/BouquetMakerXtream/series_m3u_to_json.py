#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import re
import gc
from . import bouquet_globals as glob
from .plugin import debugs

SERIES_PATTERN = re.compile(r'(S\d+|E\d+|Episode\s\d+)', re.IGNORECASE)


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
            for raw_line in infile:
                line = (raw_line or "").strip()
                if not line:
                    continue

                if line.startswith('#EXTINF'):
                    group_title = ""
                    name = ""

                    gt_pos = line.find('group-title="')
                    if gt_pos > -1:
                        end_pos = line.find('"', gt_pos + 13)
                        if end_pos > -1:
                            group_title = (line[gt_pos + 13:end_pos] or "").strip()

                    if group_title and group_title in hidden_categories:
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

                elif line.startswith(('http://', 'https://')):
                    source = (line.split()[0] or "")
                    lower_source = source.lower()

                    if "/live/" in lower_source or "/movies/" in lower_source:
                        continue

                    is_series = (
                        "/series/" in lower_source or
                        SERIES_PATTERN.search(current.get("name") or "")
                    )

                    if is_series:
                        streamid += 1
                        current["source"] = source
                        current["series_id"] = str(streamid)

                        if not first:
                            outfile.write(',')
                        json.dump(current, outfile)
                        first = False

            outfile.write(']')

    except Exception as e:
        print("Error converting m3u: %s" % str(e))

    finally:
        del current, line, raw_line
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
