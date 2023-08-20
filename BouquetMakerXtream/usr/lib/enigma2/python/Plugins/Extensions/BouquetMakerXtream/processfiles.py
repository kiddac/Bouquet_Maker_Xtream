#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, playlist_file, cfg

import json
import os
import re


try:
    from urlparse import urlparse, parse_qs
except:
    from urllib.parse import urlparse, parse_qs


def processfiles():
    # check if playlists.txt file exists in specified location
    if not os.path.isfile(playlist_file):
        open(playlist_file, "a").close()

    # check if playlists.json file exists in specified location
    if not os.path.isfile(playlists_json):
        open(playlists_json, "a").close()

    playlists_all = []

    if os.path.isfile(playlists_json):
        with open(playlists_json, "r") as f:
            try:
                playlists_all = json.load(f)
            except:
                os.remove(playlists_json)

    # check playlist.txt entries are valid
    with open(playlist_file, "r+") as f:
        lines = f.readlines()

    with open(playlist_file, "w") as f:
        for line in lines:
            line = re.sub(" +", " ", line)
            line = line.strip(" ")
            if not line.startswith("http://") and not line.startswith("https://") and not line.startswith("#"):
                line = "# " + line
            if "=mpegts" in line:
                line = line.replace("=mpegts", "=ts")
            if "=hls" in line:
                line = line.replace("=hls", "=m3u8")
            if line.strip() == "#":
                line = ""
            if line != "":
                f.write(line)

        # read entries from playlists.txt
        index = 0

        livetype = cfg.livetype.getValue()
        vodtype = cfg.vodtype.getValue()

        for line in lines:
            port = ""
            username = ""
            password = ""
            playlistformat = "m3u_plus"
            output = "ts"

            live_categories_hidden = []
            vod_categories_hidden = []
            series_categories_hidden = []

            live_streams_hidden = []
            vod_streams_hidden = []
            series_streams_hidden = []

            showlive = True
            showvod = True
            showseries = True
            prefixname = True
            # live_streams = []

            serveroffset = 0
            epgoffset = 0
            playlisttype = ""
            livecategoryorder = "original"
            livestreamorder = "original"
            vodcategoryorder = "original"
            vodstreamorder = "original"

            epgalternative = False
            epgalternativeurl = ""

            directsource = "Standard"

            if "get.php" in line:
                playlisttype = "xtream"
            else:
                playlisttype = "external"

            if not line.startswith("#") and line.startswith("http"):
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

                    host = "%s%s:%s" % (protocol, domain, port)
                else:
                    host = "%s%s" % (protocol, domain)

                if playlisttype == "xtream":
                    query = parse_qs(parsed_uri.query, keep_blank_values=True)

                    if "username" in query:
                        username = query["username"][0].strip()

                    else:
                        continue

                    if "password" in query:
                        password = query["password"][0].strip()

                    else:
                        continue

                    if "type" in query:
                        playlistformat = query["type"][0].strip()

                    if "output" in query:
                        output = query["output"][0].strip()

                    if "timeshift" in query:
                        try:
                            epgoffset = int(query["timeshift"][0].strip())
                        except:
                            pass
                    player_api = "%s/player_api.php?username=%s&password=%s" % (host, username, password)
                    xmltv_api = "%s/xmltv.php?username=%s&password=%s" % (host, username, password)

                full_url = line.partition(" #")[0].strip()

                playlist_exists = False

                if playlisttype == "xtream":
                    if playlists_all:
                        for playlist in playlists_all:

                            # extra check in case playlists.txt details have been amended
                            if "domain" in playlist["playlist_info"] and "username" in playlist["playlist_info"] and "password" in playlist["playlist_info"]:
                                if playlist["playlist_info"]["domain"] == domain and playlist["playlist_info"]["username"] == username and playlist["playlist_info"]["password"] == password:
                                    playlist_exists = True

                                    if "livecategoryorder" not in playlist["settings"]:
                                        playlist["settings"]["livecategoryorder"] = livecategoryorder

                                    if "livestreamorder" not in playlist["settings"]:
                                        playlist["settings"]["livestreamorder"] = livestreamorder

                                    if "vodcategoryorder" not in playlist["settings"]:
                                        playlist["settings"]["vodcategoryorder"] = vodcategoryorder

                                    if "vodstreamorder" not in playlist["settings"]:
                                        playlist["settings"]["vodstreamorder"] = vodstreamorder

                                    playlist["playlist_info"]["name"] = name
                                    playlist["playlist_info"]["type"] = playlistformat
                                    playlist["playlist_info"]["output"] = output
                                    playlist["playlist_info"]["full_url"] = full_url  # get.php
                                    playlist["playlist_info"]["index"] = index
                                    # playlist["data"]["data_downloaded"] = False
                                    playlist["settings"]["epgoffset"] = epgoffset

                                    if playlist["settings"]["epgalternative"] is True:
                                        if playlist["settings"]["epgalternativeurl"]:
                                            playlist["playlist_info"]["xmltv_api"] = playlist["settings"]["epgalternativeurl"]
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
                                ("type", playlistformat),
                                ("output", output),
                                ("player_api", player_api),
                                ("xmltv_api", xmltv_api),
                                ("full_url", full_url),
                                ("playlisttype", playlisttype),
                                ("valid", False),
                                ("bouquet", False)
                            ]),

                            "settings": dict([
                                ("prefixname", prefixname),

                                ("showlive", showlive),
                                ("showvod", showvod),
                                ("showseries", showseries),

                                ("livetype", livetype),
                                ("vodtype", vodtype),

                                ("livecategoryorder", livecategoryorder),
                                ("livestreamorder", livestreamorder),
                                ("vodcategoryorder", vodcategoryorder),
                                ("vodstreamorder", vodstreamorder),

                                ("epgoffset", serveroffset),
                                ("epgalternative", epgalternative),
                                ("epgalternativeurl", epgalternativeurl),
                                ("directsource", directsource)
                            ]),

                            "data": dict([
                                ("live_categories", []),
                                ("vod_categories", []),
                                ("series_categories", []),

                                ("live_streams", []),
                                ("vod_streams", []),
                                ("series_streams", []),

                                ("live_categories_hidden", live_categories_hidden),
                                ("vod_categories_hidden", vod_categories_hidden),
                                ("series_categories_hidden", series_categories_hidden),

                                ("live_streams_hidden", live_streams_hidden),
                                ("vod_streams_hidden", vod_streams_hidden),
                                ("series_streams_hidden", series_streams_hidden),

                                ("catchup_checked", False),
                                ("last_check", ""),
                                ("epg_date", ""),
                                ("data_downloaded", False),
                                ("epg_importer_files", False),
                                ("serveroffset", serveroffset)
                            ]),
                        })
                        index += 1

                elif playlisttype == "external":
                    if playlists_all:
                        for playlist in playlists_all:

                            # extra check in case playlists.txt details have been amended
                            if "full_url" in playlist["playlist_info"]:
                                if playlist["playlist_info"]["full_url"] == full_url:
                                    playlist_exists = True

                                    if "livecategoryorder" not in playlist["settings"]:
                                        playlist["settings"]["livecategoryorder"] = livecategoryorder

                                    if "livestreamorder" not in playlist["settings"]:
                                        playlist["settings"]["livestreamorder"] = livestreamorder

                                    if "vodcategoryorder" not in playlist["settings"]:
                                        playlist["settings"]["vodcategoryorder"] = vodcategoryorder

                                    if "vodstreamorder" not in playlist["settings"]:
                                        playlist["settings"]["vodstreamorder"] = vodstreamorder

                                    playlist["playlist_info"]["name"] = name
                                    playlist["playlist_info"]["index"] = index
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
                                ("playlisttype", playlisttype),
                                ("valid", False),
                                ("bouquet", False)
                            ]),

                            "settings": dict([
                                ("prefixname", prefixname),

                                ("showlive", showlive),
                                ("showvod", showvod),
                                ("showseries", showseries),

                                ("livetype", livetype),
                                ("vodtype", vodtype),

                                ("livecategoryorder", livecategoryorder),
                                ("livestreamorder", livestreamorder),
                                ("vodcategoryorder", vodcategoryorder),
                                ("vodstreamorder", vodstreamorder),
                            ]),

                            "data": dict([


                                ("live_categories", []),
                                ("vod_categories", []),
                                ("series_categories", []),

                                ("live_streams", []),
                                ("vod_streams", []),
                                ("series_streams", []),

                                ("live_categories_hidden", live_categories_hidden),
                                ("vod_categories_hidden", vod_categories_hidden),
                                ("series_categories_hidden", series_categories_hidden),

                                ("live_streams_hidden", live_streams_hidden),
                                ("vod_streams_hidden", vod_streams_hidden),
                                ("series_streams_hidden", series_streams_hidden)
                            ]),
                        })
                        index += 1

        # remove old playlists from playlists.json

        newList = []

        for playlist in playlists_all:
            for line in lines:
                if not line.startswith("#"):
                    if "full_url" in playlist["playlist_info"]:
                        if str(playlist["playlist_info"]["full_url"]) in line:
                            newList.append(playlist)
                            break
            if playlist["playlist_info"]["playlisttype"] == "local":
                path = os.path.join(cfg.locallocation.value, playlist["playlist_info"]["full_url"])
                if os.path.isfile(path):
                    newList.append(playlist)

        playlists_all = newList

    # read local files
    filename = ""

    for filename in os.listdir(cfg.locallocation.value):
        safeName = re.sub(r'[\<\>\:\"\/\\\|\?\*]', "_", str(filename))
        safeName = re.sub(r" ", "_", safeName)
        safeName = re.sub(r"_+", "_", safeName)

        os.rename(os.path.join(cfg.locallocation.value, filename), os.path.join(cfg.locallocation.value, safeName))

    for filename in os.listdir(cfg.locallocation.value):
        # print("**** filename ****", filename)
        # playlist_data = {}
        if filename.endswith(".m3u") or filename.endswith(".m3u8"):

            # print("**** file extension good ***")
            playlist_exists = False
            if playlists_all:

                for playlist in playlists_all:

                    if playlist["playlist_info"]["playlisttype"] == "local":
                        if "full_url" in playlist["playlist_info"]:
                            if playlist["playlist_info"]["full_url"] == filename:
                                playlist_exists = True

                                if "livecategoryorder" not in playlist["settings"]:
                                    playlist["settings"]["livecategoryorder"] = livecategoryorder

                                if "livestreamorder" not in playlist["settings"]:
                                    playlist["settings"]["livestreamorder"] = livestreamorder

                                if "vodcategoryorder" not in playlist["settings"]:
                                    playlist["settings"]["vodcategoryorder"] = vodcategoryorder

                                if "vodstreamorder" not in playlist["settings"]:
                                    playlist["settings"]["vodstreamorder"] = vodstreamorder

                                playlist["playlist_info"]["index"] = index
                                index += 1
                                break

            if not playlist_exists:
                # print("**** filename not exist ***", filename)

                playlists_all.append({
                    "playlist_info": dict([
                        ("index", index),
                        ("name", filename),
                        ("full_url", filename),
                        ("playlisttype", "local"),
                        ("valid", True),
                        ("bouquet", False)
                    ]),

                    "settings": dict([
                        ("prefixname", prefixname),

                        ("showlive", showlive),
                        ("showvod", showvod),
                        ("showseries", showseries),

                        ("livetype", livetype),
                        ("vodtype", vodtype),

                        ("livecategoryorder", livecategoryorder),
                        ("livestreamorder", livestreamorder),
                        ("vodcategoryorder", vodcategoryorder),
                        ("vodstreamorder", vodstreamorder),
                    ]),

                    "data": dict([
                        ("live_categories", []),
                        ("vod_categories", []),
                        ("series_categories", []),

                        ("live_streams", []),
                        ("vod_streams", []),
                        ("series_streams", []),

                        ("live_categories_hidden", live_categories_hidden),
                        ("vod_categories_hidden", vod_categories_hidden),
                        ("series_categories_hidden", series_categories_hidden),

                        ("live_streams_hidden", live_streams_hidden),
                        ("vod_streams_hidden", vod_streams_hidden),
                        ("series_streams_hidden", series_streams_hidden)

                    ]),
                })
                index += 1

    # print("write new playlists.json file")
    with open(playlists_json, "w") as f:
        json.dump(playlists_all, f)

    return playlists_all
