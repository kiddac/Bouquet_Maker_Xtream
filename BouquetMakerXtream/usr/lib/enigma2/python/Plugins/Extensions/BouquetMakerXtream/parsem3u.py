#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re

from . import _
from . import bouquet_globals as glob
from .plugin import cfg, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


def parse_m3u8_playlist(response):
    live_streams = []
    vod_streams = []
    series_streams = []
    channel_num = 0
    name = ""
    streamid = 0

    if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "local":
        local_file = os.path.join(cfg.local_location.value + glob.CURRENT_PLAYLIST["playlist_info"]["full_url"])
        with open(local_file, encoding="utf-8") as f:
            response = f.readlines()

    elif glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "external":
        response = response.splitlines()

    for line in response:
        if PYTHON_VER == 3:
            try:
                line = line.decode("utf-8")
            except Exception:
                pass

        if not line.startswith("#EXTINF") and not line.startswith("http"):
            continue

        if line.startswith("#EXTINF"):
            group_title = ""
            name = ""
            logo = ""
            epg_id = ""

            # search logo first so we can delete it if base64 png
            if "tvg-logo=" in line:
                logo = re.search('tvg-logo="(.*?)"', line).group(1).strip()
                if "data:image" in logo:
                    logo = ""
                    line = re.sub('tvg-logo="(.*?)"', "", line)

            if "group-title=" in line and "format" not in line:
                try:
                    group_title = (re.search('group-title="(.*?)"', line).group(1).strip())
                except Exception:
                    group_title = ""

            if "tvg-name=" in line:
                try:
                    name = re.search('tvg-name="(.*?)"', line).group(1).strip()
                except Exception:
                    name = line.strip().split(",")[1]

            else:
                name = line.strip().split(",")[1]

            if name == "":
                channel_num += 1
                name = _("Stream") + " " + str(channel_num)

            if "tvg-id=" in line:
                try:
                    epg_id = re.search('tvg-id=\"(.*?)\"', line).group(1).strip()
                except:
                    epg_id = ""

        elif line.startswith("http"):
            source = line.strip()
            stream_type = ""

            if "/movie/" in source:
                stream_type = "vod"
            elif "/series/" in source:
                stream_type = "series"
            elif "S0" in name or "E0" in name:
                stream_type = "series"
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
            else:
                continue

            if stream_type == "live" and glob.CURRENT_PLAYLIST["settings"]["show_live"] is True:
                if group_title == "":
                    group_title = "Uncategorised Live"
                streamid += 1
                live_streams.append([epg_id, logo, group_title, name, source, streamid])

            elif stream_type == "vod" and glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
                if group_title == "":
                    group_title = "Uncategorised VOD"

                streamid += 1
                vod_streams.append([epg_id, logo, group_title, name, source, streamid])

            elif stream_type == "series" and glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                if group_title == "":
                    group_title = "Uncategorised Series"
                streamid += 1
                series_streams.append([epg_id, logo, group_title, name, source, streamid])

            else:
                if group_title == "":
                    group_title = "Uncategorised"
                streamid += 1
                live_streams.append([epg_id, logo, group_title, name, source, streamid])

    return live_streams, vod_streams, series_streams


def make_m3u8_categories_json(live_streams, vod_streams, series_streams):
    glob.CURRENT_PLAYLIST["data"]["live_categories"] = []
    glob.CURRENT_PLAYLIST["data"]["vod_categories"] = []
    glob.CURRENT_PLAYLIST["data"]["series_categories"] = []

    for x in live_streams:
        if not glob.CURRENT_PLAYLIST["data"]["live_categories"]:
            glob.CURRENT_PLAYLIST["data"]["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.CURRENT_PLAYLIST["data"]["live_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:
                glob.CURRENT_PLAYLIST["data"]["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in vod_streams:
        if not glob.CURRENT_PLAYLIST["data"]["vod_categories"]:
            glob.CURRENT_PLAYLIST["data"]["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.CURRENT_PLAYLIST["data"]["vod_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:
                glob.CURRENT_PLAYLIST["data"]["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in series_streams:
        if not glob.CURRENT_PLAYLIST["data"]["series_categories"]:
            glob.CURRENT_PLAYLIST["data"]["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.CURRENT_PLAYLIST["data"]["series_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:
                glob.CURRENT_PLAYLIST["data"]["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})


def make_m3u8_streams_json(live_streams, vod_streams, series_streams):
    glob.CURRENT_PLAYLIST["data"]["live_streams"] = []
    glob.CURRENT_PLAYLIST["data"]["vod_streams"] = []
    glob.CURRENT_PLAYLIST["data"]["series_streams"] = []

    for x in live_streams:
        glob.CURRENT_PLAYLIST["data"]["live_streams"].append({"epg_channel_id": str(x[0]), "stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in vod_streams:
        glob.CURRENT_PLAYLIST["data"]["vod_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in series_streams:
        glob.CURRENT_PLAYLIST["data"]["series_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name": str(x[3]), "source": str(x[4]), "series_id": str(x[5]), "added": 0})
