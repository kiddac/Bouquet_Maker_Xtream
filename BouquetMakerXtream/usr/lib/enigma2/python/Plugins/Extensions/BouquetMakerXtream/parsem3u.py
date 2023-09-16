#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from .plugin import cfg, pythonVer

import os
import re


def parse_m3u8_playlist(response):
    live_streams = []
    vod_streams = []
    series_streams = []
    channelnum = 0
    name = ""
    streamid = 0

    if glob.current_playlist["playlist_info"]["playlisttype"] == "local":
        localfile = os.path.join(cfg.locallocation.value + glob.current_playlist["playlist_info"]["full_url"])
        with open(localfile) as f:
            response = f.readlines()

    elif glob.current_playlist["playlist_info"]["playlisttype"] == "external":
        response = response.splitlines()

    for line in response:
        if pythonVer == 3:
            try:
                line = line.decode("utf-8")
            except:
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
                logo = re.search('tvg-logo=\"(.*?)\"', line).group(1).strip()
                if "data:image" in logo:
                    logo = ""
                    line = re.sub('tvg-logo=\"(.*?)\"', '', line)

            if "group-title=" in line and "format" not in line:
                try:
                    group_title = re.search('group-title=\"(.*?)\"', line).group(1).strip()
                except:
                    group_title = ""

            if "tvg-name=" in line:
                try:
                    name = re.search('tvg-name=\"(.*?)\"', line).group(1).strip()
                except:
                    name = line.strip().split(",")[1]

            else:
                name = line.strip().split(",")[1]

            if name == "":
                channelnum += 1
                name = _("Stream") + " " + str(channelnum)

            if "tvg-id=" in line:
                try:
                    epg_id = re.search('tvg-id=\"(.*?)\"', line).group(1).strip()
                except:
                    epg_id = ""

        elif line.startswith("http"):
            source = line.strip()
            streamtype = ""

            if "/movie/" in source:
                streamtype = "vod"
            elif "/series/" in source:
                streamtype = "series"
            elif "S0" in name or "E0" in name:
                streamtype = "series"
            elif source.endswith(".mp4") or source.endswith(".mkv") or source.endswith("avi"):
                streamtype = "vod"
            elif source.endswith(".ts") \
                or source.endswith(".m3u8") \
                    or source.endswith(".mpd") \
                    or source.endswith("mpegts") \
                    or source.endswith(":") \
                    or "/live" in source \
                    or "/m3u8" in source \
                    or "deviceUser" in source \
                    or "deviceMac" in source \
                    or "/play/" in source \
                    or "pluto.tv" in source \
                    or (source[-1].isdigit()):
                streamtype = "live"
            else:
                continue

            if streamtype == "live" and glob.current_playlist["settings"]["showlive"] is True:
                if group_title == "":
                    group_title = "Uncategorised Live"
                streamid += 1
                live_streams.append([epg_id, logo, group_title, name, source, streamid])

            elif streamtype == "vod" and glob.current_playlist["settings"]["showvod"] is True:
                if group_title == "":
                    group_title = "Uncategorised VOD"

                streamid += 1
                vod_streams.append([epg_id, logo, group_title, name, source, streamid])

            elif streamtype == "series" and glob.current_playlist["settings"]["showseries"] is True:
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
    glob.current_playlist["data"]["live_categories"] = []
    glob.current_playlist["data"]["vod_categories"] = []
    glob.current_playlist["data"]["series_categories"] = []

    for x in live_streams:
        if not glob.current_playlist["data"]["live_categories"]:

            glob.current_playlist["data"]["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.current_playlist["data"]["live_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:

                glob.current_playlist["data"]["live_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in vod_streams:
        if not glob.current_playlist["data"]["vod_categories"]:

            glob.current_playlist["data"]["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.current_playlist["data"]["vod_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:

                glob.current_playlist["data"]["vod_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

    for x in series_streams:
        if not glob.current_playlist["data"]["series_categories"]:
            glob.current_playlist["data"]["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})
        else:
            exists = False
            for category in glob.current_playlist["data"]["series_categories"]:
                if category["category_name"] == str(x[2]):
                    exists = True
                    break
            if not exists:
                glob.current_playlist["data"]["series_categories"].append({"category_id": str(x[2]), "category_name": str(x[2])})

def make_m3u8_streams_json(live_streams, vod_streams, series_streams):
    glob.current_playlist["data"]["live_streams"] = []
    glob.current_playlist["data"]["vod_streams"] = []
    glob.current_playlist["data"]["series_streams"] = []

    for x in live_streams:
        glob.current_playlist["data"]["live_streams"].append({"epg_channel_id": str(x[0]), "stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in vod_streams:
        glob.current_playlist["data"]["vod_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "stream_id": str(x[5]), "added": 0})

    for x in series_streams:
        glob.current_playlist["data"]["series_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "series_id": str(x[5]), "added": 0})
