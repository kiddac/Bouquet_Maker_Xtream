#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from . import _
from . import bouquet_globals as glob
from .plugin import debugs


def parseM3u8Playlist(response):
    if debugs:
        print("*** parseM3u8Playlist ***")
    series_streams = []
    channel_num = 0
    streamid = 0
    url_pattern = re.compile(r'(https?://[^\s]+)')

    if isinstance(response, bytes):  # Ensure it's a string
        response = response.decode('utf-8', 'ignore')

    response_lines = response.splitlines()
    length = len(response_lines)

    skip_next = False

    for index in range(length):
        if skip_next:
            skip_next = False
            continue

        line = response_lines[index].strip()

        if not line.startswith("#EXTINF") or line == "#EXTINF:0,#EXTM3U":
            continue

        group_title = ""
        name = ""

        start_index = line.find('group-title="')
        if start_index != -1:
            start_index += len('group-title="')
            end_index = line.find('"', start_index)
            if end_index != -1:
                group_title = line[start_index:end_index].strip()

        if isinstance(glob.current_playlist["data"].get("series_categories_hidden", []), list):
            if str(group_title) in glob.current_playlist["data"]["series_categories_hidden"]:
                continue

        start_index = line.find('tvg-name="')
        if start_index != -1:
            start_index += len('tvg-name="')
            end_index = line.find('"', start_index)
            if end_index != -1:
                name = line[start_index:end_index].strip()

        if not name and ',' in line:
            name = line.strip().split(",")[-1].strip()

        name = remove_duplicate_phrases(name)

        if not name:
            channel_num += 1
            name = _("Stream") + " " + str(channel_num)

        if index + 1 < length:
            next_line = response_lines[index + 1].strip()
            url_match = url_pattern.search(next_line)
            if url_match:
                source = url_match.group(1)
                skip_next = True

                if "---" in name or "***" in name:
                    continue

                stream_type = ""

                if (("S0" in name or "E0" in name) and ("/series/" in source or "/play/" in source or source.endswith(".mp4", ".mkv", ".avi"))):
                    stream_type = "series"

                if name and source and stream_type == "series":
                    group_title = group_title if group_title else "Uncategorised Series"
                    streamid += 1
                    series_streams.append([group_title, name, source, streamid])

    data = glob.current_playlist["data"]
    data["series_streams"] = [{
        "category_id": str(x[0]),
        "name": str(x[1]),
        "source": str(x[2]),
        "series_id": str(x[3]),
        "added": 0
    } for x in series_streams]


def remove_duplicate_phrases(input_string):
    # Split input string into parts based on spaces and dashes
    parts = re.split(r'(\s+|-)', input_string)
    seen = set()
    result = []
    phrase = ""

    for part in parts:
        phrase += part
        trimmed_phrase = phrase.strip()

        if trimmed_phrase and trimmed_phrase not in seen:
            seen.add(trimmed_phrase)
            result.append(part)
            phrase = ""
        elif trimmed_phrase == "":
            result.append(part)
        else:
            # If the trimmed phrase is a duplicate, reset the phrase
            phrase = ""

    # Join the result and format spaces properly
    final_result = ''.join(result).strip()
    return remove_double_spaces(final_result)


def remove_double_spaces(input_string):
    return re.sub(r'\s{2,}', ' ', input_string)
