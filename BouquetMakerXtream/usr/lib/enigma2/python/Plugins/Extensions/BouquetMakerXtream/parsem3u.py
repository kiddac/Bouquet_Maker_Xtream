#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re

from . import _
from . import bouquet_globals as glob
from .plugin import cfg, pythonVer


def parseM3u8Playlist(response):
    live_streams = []
    vod_streams = []
    series_streams = []
    channel_num = 0
    name = ""
    streamid = 0

    playlist_type = glob.current_playlist["playlist_info"]["playlist_type"]

    if playlist_type == "local":
        local_file = os.path.join(cfg.local_location.value, glob.current_playlist["playlist_info"]["full_url"])
        with open(local_file, encoding="utf-8") as f:
            response = f.readlines()
    else:
        response = response.splitlines()

    for line in response:
        if pythonVer == 3 and isinstance(line, bytes):
            line = line.decode("utf-8")

        if not (line.startswith("#EXTINF") or line.startswith("http") or line.startswith("#EXTGRP")):
            continue

        if line.startswith("#EXTINF"):
            group_title = ""
            name = ""
            logo = ""
            epg_id = ""

            # search logo first so we can delete it if base64 png
            logo_match = re.search('tvg-logo="(.*?)"', line)
            if logo_match:
                logo = logo_match.group(1).strip()
                if logo.startswith("data:image"):
                    logo = ""
                    line = re.sub('tvg-logo="(.*?)"', "", line)

            group_title_match = re.search('group-title="(.*?)"', line)
            group_title = group_title_match.group(1).strip() if group_title_match and "format" not in line else ""

            if ',' in line:
                name_match = re.search('tvg-name="(.*?)"', line)
                name = name_match.group(1).strip() if name_match else line.strip().split(",")[1]

            if not name:
                channel_num += 1
                name = _("Stream") + " " + str(channel_num)

            epg_id_match = re.search('tvg-id="(.*?)"', line)
            epg_id = epg_id_match.group(1).strip() if epg_id_match else ""

        elif line.startswith("#EXTGRP") and not group_title:
            group_title = line.split()[-1]

        elif line.startswith("http"):
            source = line.strip()
            stream_type = ""

            if "---" in name or "***" in name:
                continue

            if "/series/" in source:
                stream_type = "series"

            elif (source.endswith(".mp4") or source.endswith(".mkv") or source.endswith("avi")) and ("S0" in name or "E0" in name):
                stream_type = "series"

            elif "/movie/" in source:
                stream_type = "vod"

            elif source.endswith(".mp4") or source.endswith(".mkv") or source.endswith("avi"):
                stream_type = "vod"

            elif (
                source.endswith(".ts")
                or source.endswith(".m3u8")
                or source.endswith(".mpd")
                or source.endswith("mpegts")
                or source.endswith(":")
                or "/live" in source
                or "/m3u8" in source
                or "deviceUser" in source
                or "deviceMac" in source
                or "/play/" in source
                or "pluto.tv" in source
                or (source[-1].isdigit())
            ):
                stream_type = "live"

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
    data["live_streams"] = []
    data["vod_streams"] = []
    data["series_streams"] = []

    for x in live_streams:
        data["live_streams"].append({"epg_channel_id": str(x[0]), "stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in vod_streams:
        data["vod_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in series_streams:
        data["series_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "series_id": str(x[5]), "added": 0})
