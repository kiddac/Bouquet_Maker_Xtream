#!/usr/bin/python
# -*- coding: utf-8 -*-

# Standard library imports
import json
import os
import re

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

# Local application/library-specific imports
from .plugin import cfg, playlist_file, playlists_json, debugs


def processFiles():
    if debugs:
        print("*** processFiles ***")
    # Check if playlists.txt file exists in specified location
    if not os.path.isfile(playlist_file):
        with open(playlist_file, "a"):
            pass

    # Check if x-playlists.json file exists in specified location
    if not os.path.isfile(playlists_json):
        with open(playlists_json, "a"):
            pass

    playlists_all = []
    prefix_name = True
    show_live = True
    show_vod = False
    show_series = False
    live_category_order = "original"
    live_stream_order = "original"
    vod_category_order = "original"
    vod_stream_order = "original"
    server_offset = 0
    epg_alternative = False
    epg_alternative_url = ""
    next_days = "0"

    if os.path.isfile(playlists_json):
        with open(playlists_json, "r") as f:
            try:
                playlists_all = json.load(f)
            except ValueError:
                os.remove(playlists_json)
                playlists_all = []
    else:
        with open(playlists_json, "w") as f:
            playlists_all = []
            json.dump(playlists_all, f, indent=4)

    # Check playlist.txt entries are valid
    with open(playlist_file, "r+") as f:
        lines = f.readlines()

    with open(playlist_file, "w") as f:
        for line in lines:
            line = re.sub(" +", " ", line)
            line = line.strip(" ")
            if not line.startswith(("http://", "https://", "#")):
                line = "# " + line
            if "=mpegts" in line:
                line = line.replace("=mpegts", "=ts")
            if "=hls" in line:
                line = line.replace("=hls", "=m3u8")
            if line.strip() == "#":
                line = ""

            playlist_type = "xtream" if "get.php" in line else "external"

            if playlist_type == "xtream" and line.startswith("http"):
                port = ""
                username = ""
                password = ""
                media_type = "m3u_plus"
                output = ""
                epg_offset = 0

                parsed_uri = urlparse(line)
                protocol = parsed_uri.scheme + "://"

                if not (protocol == "http://" or protocol == "https://"):
                    continue

                domain = parsed_uri.hostname.lower()
                name = domain

                if line.partition(" #")[-1]:
                    name = line.partition(" #")[-1].strip()

                if parsed_uri.port:
                    port = parsed_uri.port
                    host = protocol + domain + ":" + str(port)
                else:
                    host = protocol + domain

                query = parse_qs(parsed_uri.query, keep_blank_values=True)

                if "username" not in query or "password" not in query:
                    continue

                username = query["username"][0].strip()
                password = query["password"][0].strip()

                """
                if "type" in query:
                    media_type = query["type"][0].strip()
                    """

                if "output" in query:
                    output = query["output"][0].strip()
                else:
                    output = "ts"

                if output not in ["ts", "m3u8", "mpegts", "hls"]:
                    output = "ts"

                if output == "mpegts":
                    output = "ts"

                if output == "hls":
                    output = "m3u8"

                if "timeshift" in query:
                    try:
                        epg_offset = int(query["timeshift"][0].strip())
                    except ValueError:
                        pass

                if epg_offset != 0:
                    line = "%s/get.php?username=%s&password=%s&type=%s&output=%s&timeshift=%s #%s\n" % (host, username, password, media_type, output, epg_offset, name)
                else:
                    line = "%s/get.php?username=%s&password=%s&type=%s&output=%s #%s\n" % (host, username, password, media_type, output, name)

            if line != "":
                f.write(line)

        # build json data
        index = 0
        live_type = cfg.live_type.getValue()
        vod_type = cfg.vod_type.getValue()

        for line in lines:
            port = ""
            username = ""
            password = ""
            media_type = "m3u_plus"
            output = ""

            # live_streams = []

            epg_offset = 0
            playlist_type = ""

            playlist_type = "xtream" if "get.php" in line else "external"

            if line.startswith("http"):
                line = line.strip()

                parsed_uri = urlparse(line)
                protocol = parsed_uri.scheme + "://"

                if not (protocol == "http://" or protocol == "https://"):
                    continue

                domain = parsed_uri.hostname.lower()
                name = domain

                if line.partition(" #")[-1]:
                    name = line.partition(" #")[-1].strip()

                if parsed_uri.port:
                    port = parsed_uri.port
                    host = protocol + domain + ":" + str(port)
                else:
                    host = protocol + domain

                if playlist_type == "xtream":
                    query = parse_qs(parsed_uri.query, keep_blank_values=True)

                    if "username" not in query or "password" not in query:
                        continue

                    username = query["username"][0].strip()
                    password = query["password"][0].strip()

                    """
                    if "type" in query:
                        media_type = query["type"][0].strip()
                        """

                    if "output" in query:
                        output = query["output"][0].strip()
                    else:
                        output = "ts"

                    if output not in ["ts", "m3u8", "mpegts", "hls"]:
                        output = "ts"

                    if output == "mpegts":
                        output = "ts"

                    if output == "hls":
                        output = "m3u8"

                    if "timeshift" in query:
                        try:
                            epg_offset = int(query["timeshift"][0].strip())
                        except ValueError:
                            pass

                    player_api = host + "/player_api.php?username=" + username + "&password=" + password
                    xmltv_api = host + "/xmltv.php?username=" + username + "&password=" + password
                    full_url = host + "/get.php?username=" + username + "&password=" + password + "&type=" + media_type + "&output=" + output

                elif playlist_type == "external":
                    full_url = line.partition("#")[0].strip()

                playlist_exists = False

                if playlist_type == "xtream":

                    for playlist in playlists_all:
                        # extra check in case playlists.txt details have been amended
                        if ("domain" in playlist["playlist_info"] and "username" in playlist["playlist_info"] and "password" in playlist["playlist_info"]):
                            if (playlist["playlist_info"]["domain"] == domain and playlist["playlist_info"]["username"] == username and playlist["playlist_info"]["password"] == password):

                                playlist_exists = True

                                if "live_category_order" not in playlist["settings"]:
                                    playlist["settings"]["live_category_order"] = live_category_order

                                if "live_stream_order" not in playlist["settings"]:
                                    playlist["settings"]["live_stream_order"] = live_stream_order

                                if "vod_category_order" not in playlist["settings"]:
                                    playlist["settings"]["vod_category_order"] = vod_category_order

                                if "vod_stream_order" not in playlist["settings"]:
                                    playlist["settings"]["vod_stream_order"] = vod_stream_order

                                if ("next_days" not in playlist["settings"]) or ("next_days" in playlist["settings"] and playlist["settings"]["next_days"] == 0):
                                    playlist["settings"]["next_days"] = next_days

                                playlist["playlist_info"]["name"] = name
                                playlist["playlist_info"]["type"] = media_type
                                playlist["playlist_info"]["output"] = output
                                playlist["playlist_info"]["full_url"] = full_url  # get.php
                                playlist["playlist_info"]["index"] = index

                                playlist["data"]["live_streams"] = []
                                playlist["data"]["vod_streams"] = []
                                playlist["data"]["series_streams"] = []

                                playlist["settings"]["epg_offset"] = epg_offset

                                if playlist["settings"]["epg_alternative"]:
                                    if playlist["settings"]["epg_alternative_url"]:
                                        playlist["playlist_info"]["xmltv_api"] = playlist["settings"]["epg_alternative_url"]
                                else:
                                    playlist["playlist_info"]["xmltv_api"] = xmltv_api
                                index += 1
                                break

                    if not playlist_exists:
                        playlists_all.append({
                            "playlist_info": dict([
                                ("index", index),
                                ("name", name),
                                ("protocol", protocol),
                                ("domain", domain),
                                ("host", host),
                                ("port", port),
                                ("username", username),
                                ("password", password),
                                ("type", media_type),
                                ("output", output),
                                ("player_api", player_api),
                                ("xmltv_api", xmltv_api),
                                ("full_url", full_url),
                                ("playlist_type", playlist_type),
                                ("valid", False),
                                ("bouquet", False)
                            ]),

                            "settings": dict([
                                ("prefix_name", prefix_name),
                                ("show_live", show_live),
                                ("show_vod", show_vod),
                                ("show_series", show_series),
                                ("live_type", live_type),
                                ("vod_type", vod_type),
                                ("live_category_order", live_category_order),
                                ("live_stream_order", live_stream_order),
                                ("vod_category_order", vod_category_order),
                                ("vod_stream_order", vod_stream_order),
                                ("epg_offset", server_offset),
                                ("epg_alternative", epg_alternative),
                                ("epg_alternative_url", epg_alternative_url),
                                ("next_days", next_days)
                            ]),
                            "data": dict([
                                ("live_categories", []),
                                ("vod_categories", []),
                                ("series_categories", []),
                                ("live_streams", []),
                                ("vod_streams", []),
                                ("series_streams", []),
                                ("live_categories_hidden", []),
                                ("vod_categories_hidden", []),
                                ("series_categories_hidden", []),
                                ("live_streams_hidden", []),
                                ("vod_streams_hidden", []),
                                ("series_streams_hidden", []),
                                ("server_offset", server_offset)
                            ]),
                        })
                        index += 1

                elif playlist_type == "external":
                    if playlists_all:
                        for playlist in playlists_all:
                            # extra check in case playlists.txt details have been amended
                            if "full_url" in playlist["playlist_info"] and playlist["playlist_info"]["full_url"] == full_url:
                                playlist_exists = True

                                if "live_category_order" not in playlist["settings"]:
                                    playlist["settings"]["live_category_order"] = live_category_order

                                if "live_stream_order" not in playlist["settings"]:
                                    playlist["settings"]["live_stream_order"] = live_stream_order

                                if "vod_category_order" not in playlist["settings"]:
                                    playlist["settings"]["vod_category_order"] = vod_category_order

                                if "vod_stream_order" not in playlist["settings"]:
                                    playlist["settings"]["vod_stream_order"] = vod_stream_order

                                playlist["playlist_info"]["name"] = name
                                playlist["playlist_info"]["index"] = index

                                playlist["data"]["live_streams"] = []
                                playlist["data"]["vod_streams"] = []
                                playlist["data"]["series_streams"] = []

                                index += 1
                                break

                    if not playlist_exists:
                        playlists_all.append({
                            "playlist_info": dict([
                                ("index", index),
                                ("name", name),
                                ("protocol", protocol),
                                ("domain", domain),
                                ("host", host),
                                ("port", port),
                                ("full_url", full_url),
                                ("playlist_type", playlist_type),
                                ("valid", False),
                                ("bouquet", False)
                            ]),
                            "settings": dict([
                                ("prefix_name", prefix_name),
                                ("show_live", show_live),
                                ("show_vod", show_vod),
                                ("show_series", show_series),
                                ("live_type", live_type),
                                ("vod_type", vod_type),
                                ("live_category_order", live_category_order),
                                ("live_stream_order", live_stream_order),
                                ("vod_category_order", vod_category_order),
                                ("vod_stream_order", vod_stream_order)
                            ]),
                            "data": dict([
                                ("live_categories", []),
                                ("vod_categories", []),
                                ("series_categories", []),
                                ("live_streams", []),
                                ("vod_streams", []),
                                ("series_streams", []),
                                ("live_categories_hidden", []),
                                ("vod_categories_hidden", []),
                                ("series_categories_hidden", []),
                                ("live_streams_hidden", []),
                                ("vod_streams_hidden", []),
                                ("series_streams_hidden", [])
                            ]),
                        })
                        index += 1

        # remove old playlists from playlists.json
        newList = []

        for playlist in playlists_all:
            for line in lines:
                if not line.startswith("#"):
                    if playlist["playlist_info"]["playlist_type"] == "xtream":
                        if "host" in playlist["playlist_info"] and "username" in playlist["playlist_info"] and "password" in playlist["playlist_info"] and str(playlist["playlist_info"]["domain"]) in line and str(playlist["playlist_info"]["username"]) in line and str(playlist["playlist_info"]["password"]) in line:
                            newList.append(playlist)
                            break

                    elif playlist["playlist_info"]["playlist_type"] == "external":
                        if "full_url" in playlist["playlist_info"] and str(playlist["playlist_info"]["full_url"]) in line:
                            newList.append(playlist)
                            break

            if playlist["playlist_info"]["playlist_type"] == "local":
                path = os.path.join(cfg.local_location.value, playlist["playlist_info"]["full_url"])
                if os.path.isfile(path):
                    newList.append(playlist)

        playlists_all = newList

    # read local files
    filename = ""

    for filename in os.listdir(cfg.local_location.value):
        safe_name = re.sub(r'[\'\<\>\:\"\/\\\|\?\*\(\)\[\]]', "_", str(filename))
        safe_name = re.sub(r" ", "_", safe_name)
        safe_name = re.sub(r"_+", "_", safe_name)

        os.rename(os.path.join(cfg.local_location.value, filename), os.path.join(cfg.local_location.value, safe_name))

    for filename in os.listdir(cfg.local_location.value):
        if filename.endswith(".m3u") or filename.endswith(".m3u8"):
            playlist_exists = False
            if playlists_all:
                for playlist in playlists_all:
                    if playlist["playlist_info"]["playlist_type"] == "local" and "full_url" in playlist["playlist_info"] and playlist["playlist_info"]["full_url"] == filename:
                        playlist_exists = True

                        if "live_category_order" not in playlist["settings"]:
                            playlist["settings"]["live_category_order"] = live_category_order

                        if "live_stream_order" not in playlist["settings"]:
                            playlist["settings"]["live_stream_order"] = live_stream_order

                        if "vod_category_order" not in playlist["settings"]:
                            playlist["settings"]["vod_category_order"] = vod_category_order

                        if "vod_stream_order" not in playlist["settings"]:
                            playlist["settings"]["vod_stream_order"] = vod_stream_order

                        playlist["playlist_info"]["index"] = index

                        playlist["data"]["live_streams"] = []
                        playlist["data"]["vod_streams"] = []
                        playlist["data"]["series_streams"] = []

                        index += 1
                        break

            if not playlist_exists:
                playlists_all.append({
                    "playlist_info": dict([
                        ("index", index),
                        ("name", filename),
                        ("full_url", filename),
                        ("playlist_type", "local"),
                        ("valid", True),
                        ("bouquet", False)
                    ]),
                    "settings": dict([
                        ("prefix_name", prefix_name),
                        ("show_live", show_live),
                        ("show_vod", show_vod),
                        ("show_series", show_series),
                        ("live_type", live_type),
                        ("vod_type", vod_type),
                        ("live_category_order", live_category_order),
                        ("live_stream_order", live_stream_order),
                        ("vod_category_order", vod_category_order),
                        ("vod_stream_order", vod_stream_order)
                    ]),
                    "data": dict([
                        ("live_categories", []),
                        ("vod_categories", []),
                        ("series_categories", []),
                        ("live_streams", []),
                        ("vod_streams", []),
                        ("series_streams", []),
                        ("live_categories_hidden", []),
                        ("vod_categories_hidden", []),
                        ("series_categories_hidden", []),
                        ("live_streams_hidden", []),
                        ("vod_streams_hidden", []),
                        ("series_streams_hidden", [])
                    ]),
                })
                index += 1

    # Write new x-playlists.json file
    with open(playlists_json, "w") as f:
        json.dump(playlists_all, f, indent=4)

    return playlists_all
