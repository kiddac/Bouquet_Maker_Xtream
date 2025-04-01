#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import os
import codecs
from . import _
from . import bouquet_globals as glob

from .plugin import cfg


def parseM3u8Playlist(response):
    # Handle response depending on whether it's local or downloaded

    playlist_type = glob.current_playlist["playlist_info"]["playlist_type"]

    if playlist_type == "local":
        local_file = os.path.join(cfg.local_location.value, glob.current_playlist["playlist_info"]["full_url"])
        with codecs.open(local_file, "r", encoding="utf-8") as f:
            response_lines = f.readlines()
    else:
        response_lines = response.splitlines()

    length = len(response_lines)
    live_streams = []
    vod_streams = []
    series_streams = []
    skip_next = False
    streamid = 0
    channel_num = 0

    # Patterns for extracting details
    logo_pattern = re.compile(r'tvg-logo="([^"]+)"')
    epg_id_pattern = re.compile(r'tvg-id="([^"]+)"')
    url_pattern = re.compile(r'(https?://[^\s]+)')

    for index in range(length):
        if skip_next:
            skip_next = False
            continue

        line = response_lines[index].strip()

        # If a new #EXTINF line is encountered, restart the process of looking for a URL
        if line.startswith("#EXTINF") and line != "#EXTINF:0,#EXTM3U":
            group_title = ""
            name = ""
            logo = ""
            epg_id = ""

            logo_match = logo_pattern.search(line)
            if logo_match:
                logo = logo_match.group(1).strip()
                if logo.startswith("data:image"):
                    logo = ""
                    line = logo_pattern.sub('', line)

            # Extract group-title from #EXTINF line
            start_index = line.find('group-title="')
            if start_index != -1:
                start_index += len('group-title="')
                end_index = line.find('"', start_index)
                if end_index != -1:
                    group_title = line[start_index:end_index].strip()

            # Extract tvg-name from #EXTINF line
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

            # Extract tvg-id from #EXTINF line
            epg_id_match = epg_id_pattern.search(line)
            if epg_id_match:
                epg_id = epg_id_match.group(1).strip()

            # Check for URL in the next line or two lines after
            source = None
            if index + 1 < length:
                next_line = response_lines[index + 1].strip()
                url_match = url_pattern.search(next_line)
                if url_match:
                    source = url_match.group(1)
                    skip_next = True
                elif next_line.startswith("#EXTGRP") and not group_title:
                    group_title = next_line.split(":", 1)[-1].strip()

                # If still no URL, check the next one after #EXTGRP
                if not source and index + 2 < length:
                    next_line = response_lines[index + 2].strip()
                    url_match = url_pattern.search(next_line)
                    if url_match:
                        source = url_match.group(1)
                        skip_next = True

            # If a URL wasn't found after expected lines, skip this entry and continue
            if not source:
                continue

            # Determine the stream type based on the URL and name
            stream_type = ""
            
            if "/series/" in source or "/play/" in source or (source.endswith((".mp4", ".mkv", ".avi")) and ("S0" in name or "E0" in name)):
                stream_type = "series"
            elif "/movie/" in source or source.endswith((".mp4", ".mkv", ".avi")):
                stream_type = "vod"
            elif (
                source.endswith((".ts", ".m3u8", ".mpd", "mpegts", ":")) or
                "/live" in source or
                "/m3u8" in source or
                "deviceUser" in source or
                "deviceMac" in source or
                "/play/" in source or
                "pluto.tv" in source or
                (source[-1].isdigit())
            ):
                stream_type = "live"

            # Append the stream to the appropriate list based on stream type
            if name and source:
                if stream_type == "live":
                    group_title = group_title if group_title else "Uncategorised Live"
                    streamid += 1
                    live_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif stream_type == "vod":
                    group_title = group_title if group_title else "Uncategorised VOD"
                    streamid += 1
                    vod_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif stream_type == "series":
                    group_title = group_title if group_title else "Uncategorised Series"
                    streamid += 1
                    series_streams.append([epg_id, logo, group_title, name, source, streamid])

                else:
                    group_title = group_title if group_title else "Uncategorised"
                    streamid += 1
                    live_streams.append([epg_id, logo, group_title, name, source, streamid])

    return live_streams, vod_streams, series_streams


def makeM3u8CategoriesJson(live_streams, vod_streams, series_streams):
    data = glob.current_playlist["data"]
    data["live_categories"] = []
    data["vod_categories"] = []
    data["series_categories"] = []

    for x in live_streams:
        if not data["live_categories"]:
            data["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = any(category["category_name"] == str(x[2]) for category in data["live_categories"])
            if not exists:
                data["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in vod_streams:
        if not data["vod_categories"]:
            data["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = any(category["category_name"] == str(x[2]) for category in data["vod_categories"])
            if not exists:
                data["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in series_streams:
        if not data["series_categories"]:
            data["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = any(category["category_name"] == str(x[2]) for category in data["series_categories"])
            if not exists:
                data["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})


def makeM3u8StreamsJson(live_streams, vod_streams, series_streams):
    data = glob.current_playlist["data"]

    data["live_streams"] = [{"epg_channel_id": str(x[0]), "stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0} for x in live_streams]

    data["vod_streams"] = [{"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0} for x in vod_streams]

    data["series_streams"] = [{"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "series_id": str(x[5]), "added": 0} for x in series_streams]


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
