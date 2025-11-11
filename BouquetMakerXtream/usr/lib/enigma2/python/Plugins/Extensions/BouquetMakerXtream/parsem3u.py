#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import os
import codecs
from . import _
from . import bouquet_globals as glob
from .plugin import cfg

# Pre-compile only the complex regex patterns we need
SERIES_PATTERN = re.compile(r'(S\d+|E\d+)', re.IGNORECASE)
DOUBLE_SPACES_PATTERN = re.compile(r'\s{2,}')


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

    index = 0
    while index < length:
        if skip_next:
            skip_next = False
            index += 1
            continue

        line = response_lines[index].strip()

        # If a new #EXTINF line is encountered, restart the process of looking for a URL
        if line.startswith("#EXTINF") and line != "#EXTINF:0,#EXTM3U":
            group_title = ""
            name = ""
            logo = ""
            epg_id = ""

            # Extract logo using string methods (faster than regex)
            logo_pos = line.find('tvg-logo="')
            if logo_pos > -1:
                end_pos = line.find('"', logo_pos + 10)
                if end_pos > -1:
                    logo = line[logo_pos + 10:end_pos].strip()
                    if logo.startswith("data:image"):
                        logo = ""
                        # Remove the logo attribute from line
                        line = line[:logo_pos] + line[end_pos + 1:]

            # Extract group-title using string methods
            gt_pos = line.find('group-title="')
            if gt_pos > -1:
                end_pos = line.find('"', gt_pos + 13)
                if end_pos > -1:
                    group_title = line[gt_pos + 13:end_pos].strip()

            # Extract tvg-name using string methods
            name_pos = line.find('tvg-name="')
            if name_pos > -1:
                end_pos = line.find('"', name_pos + 10)
                if end_pos > -1:
                    name = line[name_pos + 10:end_pos].strip()

            # Extract tvg-id using string methods
            epg_pos = line.find('tvg-id="')
            if epg_pos > -1:
                end_pos = line.find('"', epg_pos + 8)
                if end_pos > -1:
                    epg_id = line[epg_pos + 8:end_pos].strip()

            # Fallback: name after last comma
            if not name and ',' in line:
                name = line.strip().split(",")[-1].strip()

            name = remove_duplicate_phrases(name)

            if not name:
                channel_num += 1
                name = _("Stream") + " " + str(channel_num)

            # Check for URL in the next line or two lines after
            source = None
            if index + 1 < length:
                next_line = response_lines[index + 1].strip()

                # Fast URL check without regex
                if next_line.startswith(('http://', 'https://', 'rtsp://')):
                    source = next_line.split()[0]  # Take first token
                    skip_next = True
                elif next_line.startswith("#EXTGRP") and not group_title:
                    group_title = next_line.split(":", 1)[-1].strip()
                    # Check next line for URL
                    if index + 2 < length:
                        next_next_line = response_lines[index + 2].strip()
                        if next_next_line.startswith(('http://', 'https://', 'rtsp://')):
                            source = next_next_line.split()[0]
                            skip_next = True

            # If a URL wasn't found after expected lines, skip this entry and continue
            if not source:
                index += 1
                continue

            # Determine the stream type based on the URL and name
            stream_type = ""
            lower_source = source.lower()

            # Early stream type detection with optimized checks
            if "/series/" in lower_source and "/live/" not in lower_source and "/movie/" not in lower_source:
                stream_type = "series"
            elif "/movie/" in lower_source or lower_source.endswith((".mp4", ".mkv", ".avi")):
                stream_type = "vod"
            elif (
                lower_source.endswith((".ts", ".m3u8", ".mpd", "mpegts", ":")) or
                "/live" in lower_source or
                "/m3u8" in lower_source or
                "deviceuser" in lower_source or
                "devicemac" in lower_source or
                "/play/" in lower_source or
                "pluto.tv" in lower_source or
                (source[-1].isdigit())
            ):
                stream_type = "live"
            else:
                # Fallback: check for series pattern in name
                if SERIES_PATTERN.search(name):
                    stream_type = "series"
                else:
                    stream_type = "live"  # Default to live

            # Append the stream to the appropriate list based on stream type
            if name and source:
                if stream_type == "live" and glob.current_playlist["settings"]["show_live"]:
                    group_title = group_title if group_title else "Uncategorised Live"
                    streamid += 1
                    live_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif stream_type == "vod" and glob.current_playlist["settings"]["show_vod"]:
                    group_title = group_title if group_title else "Uncategorised VOD"
                    streamid += 1
                    vod_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif stream_type == "series" and glob.current_playlist["settings"]["show_series"]:
                    group_title = group_title if group_title else "Uncategorised Series"
                    streamid += 1
                    series_streams.append([epg_id, logo, group_title, name, source, streamid])

        index += 1

    return live_streams, vod_streams, series_streams


def remove_duplicate_phrases(input_string):
    if not input_string:
        return input_string

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
    return DOUBLE_SPACES_PATTERN.sub(' ', input_string)
