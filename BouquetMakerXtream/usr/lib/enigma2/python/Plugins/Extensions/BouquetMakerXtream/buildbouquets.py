#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import parsem3u
from . import seriesparsem3u
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .plugin import epgimporter, cfg, playlists_json, skin_directory, debugs, dir_etc

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

import json
import os


try:
    from urllib import quote
except:
    from urllib.parse import quote

try:
    from xml.dom import minidom
except:
    pass


class BmxBuildBouquets(Screen):
    def __init__(self, session):
        if debugs:
            print("*** init ***")

        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "progress.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Building Bouquets")
        self.categories = []

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.void,
            "cancel": self.void,
        }, -2)

        self["action"] = Label(_("Building Bouquets..."))
        self["info"] = Label("")
        self["progress"] = ProgressBar()
        self["status"] = Label("")

        self.bouquet_tv = False
        self.userbouquet = False
        self.total_count = 0
        self.unique_ref = 0
        self.progress_value = 0
        self.progress_range = 0

        self.playlists_all = bmx.getPlaylistJson()
        self.playlist_info = glob.current_playlist["playlist_info"]
        self.settings = glob.current_playlist["settings"]
        self.data = glob.current_playlist["data"]
        self.original_name = glob.original_name
        self.name = bmx.safeName(self.playlist_info["name"])

        if self.playlist_info["playlist_type"] == "xtream":
            # Each content type has its own process multiplier
            self.progress_range += (
                (2 * self.settings["show_live"]) +
                (2 * self.settings["show_vod"]) +
                (4 * self.settings["show_series"])
            )
        else:
            self.progress_range += 1  # Base range for non-xtream playlists
            self.progress_range += sum([
                self.settings["show_live"],
                self.settings["show_vod"],
                self.settings["show_series"]
            ])

        if self.playlist_info["playlist_type"] == "xtream":
            self.player_api = self.playlist_info["player_api"]
            self.xmltv_api = str(self.playlist_info["xmltv_api"])
            try:
                if "next_days" in self.settings and self.settings["next_days"] != "0":
                    self.xmltv_api = str(self.playlist_info["xmltv_api"]) + "&next_days=" + str(self.settings["next_days"])
            except:
                pass

            self.username = self.playlist_info["username"]
            self.password = self.playlist_info["password"]
            self.output = self.playlist_info["output"]

            self.live_categories_api = self.player_api + "&action=get_live_categories"
            self.vod_categories_api = self.player_api + "&action=get_vod_categories"
            self.series_categories_api = self.player_api + "&action=get_series_categories"

            self.live_streams_api = self.player_api + "&action=get_live_streams"
            self.vod_streams_api = self.player_api + "&action=get_vod_streams"
            self.series_streams_api = self.player_api + "&action=get_series"

        elif self.playlist_info["playlist_type"] == "external":
            self.external_url = self.playlist_info["full_url"]

        elif self.playlist_info["playlist_type"] == "local":
            self.local_file = self.playlist_info["full_url"]

        if self.playlist_info["playlist_type"] != "local":
            protocol = self.playlist_info["protocol"]
            domain = self.playlist_info["domain"]
            port = self.playlist_info["port"]
            self.host = protocol + domain + (":" + str(port) if port else "")
            self.host_encoded = quote(self.host)

        full_url = self.playlist_info["full_url"]
        for j in str(full_url):
            value = ord(j)
            self.unique_ref += value

        self.starttimer = eTimer()
        try:
            self.starttimer_conn = self.starttimer.timeout.connect(self.start)
        except:
            self.starttimer.callback.append(self.start)
        self.starttimer.start(100, True)

    def void(self):
        if debugs:
            print("*** void ***")
        pass

    def nextJob(self, actiontext, function):
        if debugs:
            print("*** nextJob ***", actiontext)
        self["action"].setText(actiontext)
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(function)
        except:
            self.timer.callback.append(function)
        self.timer.start(50, True)

    def start(self):
        if debugs:
            print("*** start ***")

        glob.get_series_failed = False
        self["progress"].setRange((0, self.progress_range))
        self["progress"].setValue(self.progress_value)
        self.deleteExistingRefs()

        self.timer = eTimer()

        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(10, True)

    def deleteExistingRefs(self):
        if debugs:
            print("*** deleteExistingRefs ***")
        with open("/etc/enigma2/bouquets.tv", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            f.truncate()

            for line in lines:
                if "bouquetmakerxtream_live_" + str(self.name) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(self.name) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(self.name) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(self.name) + ".tv" in line:
                    continue
                if "bouquetmakerxtream_live_" + str(self.original_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(self.original_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(self.original_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(self.original_name) + ".tv" in line:
                    continue
                f.write(line)

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_" + str(self.name))

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.original_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.original_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.original_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_" + str(self.original_name))

        if epgimporter:
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.name))
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.original_name))

    def makeUrlList(self):
        if debugs:
            print("*** makeUrlList ***")

        if self.playlist_info["playlist_type"] == "xtream":
            if self.settings["show_live"]:
                self.nextJob(_("Downloading live data..."), self.downloadXtreamLive)
                # self.downloadXtreamLive()

            elif self.settings["show_vod"]:
                self.nextJob(_("Downloading VOD data..."), self.downloadXtreamVod)
                # self.downloadXtreamVod()

            elif self.settings["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadXtreamSeries)
                # self.downloadXtreamSeries()

        elif self.playlist_info["playlist_type"] == "external":
            self.nextJob(_("Downloading external playlist..."), self.downloadExternal)
            # self.downloadExternal()

        elif self.playlist_info["playlist_type"] == "local":
            self.nextJob(_("Loading local playlist..."), self.parseLocal)
            # self.parseLocal()

    def downloadXtreamLive(self):
        if debugs:
            print("*** downloadXtreamLive ***")

        # self.level = 1
        self.live_categories = []
        self.live_streams = []

        self.url_list = [[self.live_categories_api, 0], [self.live_streams_api, 3]]

        for url in self.url_list:
            result = bmx.downloadXtreamApiCategory(url)

            category = result[0]
            response = result[1]

            if response:
                if category == 0:
                    self.live_categories = response

                elif category == 3:
                    response = (
                        {
                            "name": item.get("name"),
                            "stream_id": item.get("stream_id"),
                            "stream_icon": item.get("stream_icon"),
                            "epg_channel_id": item.get("epg_channel_id"),
                            "added": item.get("added"),
                            "category_id": item.get("category_id"),
                            "custom_sid": item.get("custom_sid"),
                            "tv_archive": item.get("tv_archive"),
                        }
                        for item in response if all(k in item for k in [
                            "name", "stream_id", "stream_icon", "epg_channel_id",
                            "added", "category_id", "custom_sid", "tv_archive"
                        ])
                    )
                    self.live_streams = list(response)
                response = None

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def downloadXtreamVod(self):
        if debugs:
            print("*** downloadXtreamVod ***")

        # self.level = 1
        self.vod_categories = []
        self.vod_streams = []

        self.url_list = [[self.vod_categories_api, 1], [self.vod_streams_api, 4]]

        for url in self.url_list:
            result = bmx.downloadXtreamApiCategory(url)

            category = result[0]
            response = result[1]

            if response:
                if category == 1:
                    self.vod_categories = response
                elif category == 4:
                    response = (
                        {
                            "name": item.get("name"),
                            "stream_id": item.get("stream_id"),
                            "added": item.get("added"),
                            "category_id": item.get("category_id"),
                            "container_extension": item.get("container_extension")
                        }
                        for item in response if all(k in item for k in [
                            "name", "stream_id", "added", "category_id", "container_extension"
                        ])
                    )
                    self.vod_streams = list(response)

                response = None

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing VOD data..."), self.loadVod)

    def downloadXtreamSeries(self):
        if debugs:
            print("*** downloadXtreamSeries ***")

        self.series_categories = []
        self.series_streams = []

        self.url_list = [[self.series_categories_api, 2], [self.series_streams_api, 5]]

        for url in self.url_list:
            result = bmx.downloadXtreamApiCategory(url)

            category = result[0]
            response = result[1]

            if response:
                if category == 2:
                    self.series_categories = response

                elif category == 5:
                    response = (
                        {
                            "name": item.get("name"),
                            "series_id": item.get("series_id"),
                            "last_modified": item.get("last_modified"),
                            "category_id": item.get("category_id")
                        }
                        for item in response if all(k in item for k in [
                            "name", "series_id", "last_modified", "category_id"
                        ])
                    )
                    self.series_streams = list(response)
                response = None

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Download series get.php file..."), self.loadSeries)

    def downloadExternal(self):
        if debugs:
            print("*** downloadExternal ***")

        response = bmx.downloadM3U8File(self.external_url)

        if response:
            self.parseFullM3u8Data(response)
            response = None

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing external data..."), self.loadLive)

    def parseLocal(self):
        if debugs:
            print("*** parseLocal (load local file) ***")

        # Build the full local file path
        local_path = os.path.join(dir_etc, self.local_file)

        # Check if the file exists before reading
        if os.path.exists(local_path):
            try:
                with open(local_path, "r") as f:
                    response = f.read()
                if response:
                    self.parseFullM3u8Data(response)
                    response = None
            except Exception as e:
                if debugs:
                    print("Error reading local file:", e)
        else:
            if debugs:
                print("Local file not found:", local_path)

        self.nextJob(_("Processing local data..."), self.loadLive)

    def parseFullM3u8Data(self, response=None):
        if debugs:
            print("*** parseFullM3u8Data ***")

        # --- Step 1: Parse the playlist streams ---
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parseM3u8Playlist(response)

        # --- Step 2: Build categories ---
        if debugs:
            print("*** Building M3U8 categories ***")

        live_cats = set()
        vod_cats = set()
        series_cats = set()

        self.live_categories = []
        self.vod_categories = []
        self.series_categories = []

        for x in self.live_streams:
            cat_name = str(x[2])
            if cat_name not in live_cats:
                live_cats.add(cat_name)
                self.live_categories.append({"category_id": cat_name, "category_name": cat_name})

        for x in self.vod_streams:
            cat_name = str(x[2])
            if cat_name not in vod_cats:
                vod_cats.add(cat_name)
                self.vod_categories.append({"category_id": cat_name, "category_name": cat_name})

        for x in self.series_streams:
            cat_name = str(x[2])
            if cat_name not in series_cats:
                series_cats.add(cat_name)
                self.series_categories.append({"category_id": cat_name, "category_name": cat_name})

        # --- Step 3: Build JSON-style stream lists ---
        if debugs:
            print("*** Building M3U8 stream JSON data ***")

        self.live_streams = [
            {
                "epg_channel_id": str(x[0]),
                "stream_icon": str(x[1]),
                "category_id": str(x[2]),
                "name": str(x[3]),
                "source": str(x[4]),
                "stream_id": str(x[5]),
                "added": 0
            }
            for x in self.live_streams
        ]

        self.vod_streams = [
            {
                "stream_icon": str(x[1]),
                "category_id": str(x[2]),
                "name": str(x[3]),
                "source": str(x[4]),
                "stream_id": str(x[5]),
                "added": 0
            }
            for x in self.vod_streams
        ]

        self.series_streams = [
            {
                "stream_icon": str(x[1]),
                "category_id": str(x[2]),
                "name": str(x[3]),
                "source": str(x[4]),
                "series_id": str(x[5]),
                "added": 0
            }
            for x in self.series_streams
        ]

        if debugs:
            print("*** M3U8 parsing complete ***")

    def loadLive(self):
        if debugs:
            print("*** loadLive ***")

        if glob.current_playlist["settings"]["show_live"] and self.live_categories and self.live_streams:

            self.clearCaches()
            self.live_stream_data = []
            stream_type = self.settings["live_type"]

            if self.settings["live_category_order"] == "alphabetical":
                self.live_categories.sort(key=lambda k: k["category_name"].lower())

            if self.settings["live_stream_order"] == "alphabetical":
                self.live_streams.sort(key=lambda x: x["name"].lower())

            elif self.settings["live_stream_order"] == "added":
                self.live_streams.sort(key=lambda x: x["added"], reverse=True)

            # Convert to sets for faster membership testing
            live_categories_hidden = set(self.data["live_categories_hidden"])
            live_streams_hidden = set(self.data["live_streams_hidden"])

            for channel in self.live_streams:
                category_id = channel.get("category_id")
                name = channel.get("name") or ""
                name = name.replace(":", "").replace('"', "").replace('•', "-").strip("- ").strip()
                stream_id = channel.get("stream_id")

                if str(category_id) in live_categories_hidden or str(stream_id) in live_streams_hidden:
                    continue

                try:
                    stream_id = int(stream_id)
                except:
                    continue

                catchup = int(channel.get("tv_archive", 0))

                if cfg.catchup.value and catchup == 1:
                    name = str(cfg.catchup_prefix.value) + str(name)

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - int(bouquet_id1 * 65535)
                except:
                    continue

                service_ref = "1:0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:http%3a//example.m3u8"
                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"

                if "custom_sid" in channel and channel["custom_sid"] and str(channel["custom_sid"]) not in ("null", "None", "0", ":0:0:0:0:0:0:0:0:0:") and len(channel["custom_sid"]) > 16:
                    custom_sid = str(channel["custom_sid"])
                    if custom_sid[0].isdigit():
                        custom_sid = custom_sid[1:]

                    service_ref = str(":".join(custom_sid.split(":")[:7])) + ":0:0:0:http%3a//example.m3u8"

                xml_str = ""
                channel_id = channel.get("epg_channel_id")

                if channel_id:
                    channel_id = channel_id.replace("&", "&amp;")
                    xml_str = '\t<channel id="' + str(channel_id) + '">' + str(service_ref) + "</channel><!-- " + str(name) + " -->\n"

                bouquet_string = ""

                if self.playlist_info["playlist_type"] == "xtream":
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/live/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(self.output) + ":" + str(name) + "\n"
                else:
                    source = quote(channel.get("source", ""))
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                self.live_stream_data.append({
                    "category_id": str(category_id),
                    "xml_str": str(xml_str),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })

            if self.live_stream_data:

                if cfg.groups.value and not self.bouquet_tv:
                    self.buildBouquetTvGroupedFile()

                bouquet_tv_string = ""

                if cfg.groups.value and not self.userbouquet:
                    bouquet_tv_string += "#NAME " + str(self.playlist_info["name"]) + "\n"

                bouquet_filename = ""

                # Create dictionary for faster category lookups (reduces repeated scans)
                cat_map = {}
                for stream in self.live_stream_data:
                    cat_id = stream["category_id"]
                    if cat_id not in cat_map:
                        cat_map[cat_id] = []
                    cat_map[cat_id].append(stream)

                for category in self.live_categories:
                    category_id = category.get("category_id")

                    if not category_id or str(category_id) in live_categories_hidden or str(category_id) not in cat_map:
                        continue

                    if cfg.groups.value:
                        bouquet_filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    else:
                        bouquet_filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_live_" + str(self.name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

                if bouquet_filename:
                    with open(bouquet_filename, "a+") as f:
                        f.write(str(bouquet_tv_string))

                    for category in self.live_categories:
                        category_id = category.get("category_id")

                        if not category_id or str(category_id) in live_categories_hidden or str(category_id) not in cat_map:
                            continue

                        bouquet_title = self.name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""

                        if self.settings["prefix_name"] and not cfg.groups.value:
                            output_string += "#NAME " + self.name + " - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + category["category_name"] + "\n"

                        for stream in cat_map[str(category_id)]:
                            output_string += stream["bouquet_string"]

                        if cfg.groups.value:
                            bouquet_filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"
                        else:
                            bouquet_filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"

                        with open(bouquet_filename, "w+") as f:
                            f.write(output_string)

                # Free up memory once finished
                cat_map.clear()

            self.progress_value += 1
            self["progress"].setValue(self.progress_value)

            # Continue to next section
            if self.playlist_info["playlist_type"] == "xtream":
                if self.live_categories and epgimporter:
                    self.buildXmltvSource()
                self.live_categories = []
                self.live_streams = []
                self.live_stream_data = []
                if self.settings["show_vod"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadXtreamVod)
                elif self.settings["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadXtreamSeries)
                else:
                    self.finished()
                    return
            else:
                self.live_categories = []
                self.live_streams = []
                self.live_stream_data = []
                if self.settings["show_vod"]:
                    self.nextJob(_("Process VOD data..."), self.loadVod)
                elif self.settings["show_series"]:
                    self.nextJob(_("Processing series data..."), self.loadSeries)
                else:
                    self.finished()
                    return

    def loadVod(self):
        if debugs:
            print("*** loadVod ***")

        if glob.current_playlist["settings"]["show_vod"] and self.vod_categories and self.vod_streams:

            self.clearCaches()
            self.vod_stream_data = []
            stream_type = self.settings["vod_type"]

            if self.settings["vod_category_order"] == "alphabetical":
                self.vod_categories.sort(key=lambda k: k["category_name"].lower())

            if self.settings["vod_stream_order"] == "alphabetical":
                self.vod_streams.sort(key=lambda x: x["name"].lower())

            elif self.settings["vod_stream_order"] == "added":
                self.vod_streams.sort(key=lambda x: x["added"], reverse=True)

            # Convert to sets for faster membership testing

            vod_categories_hidden = set(self.data["vod_categories_hidden"])
            vod_streams_hidden = set(self.data["vod_streams_hidden"])

            for channel in self.vod_streams:
                category_id = channel.get("category_id")
                name = channel.get("name") or ""
                name = name.replace(":", "").replace('"', "").replace('•', "-").strip("- ").strip()
                stream_id = channel.get("stream_id")

                if str(category_id) in vod_categories_hidden or str(stream_id) in vod_streams_hidden:
                    continue

                try:
                    stream_id = int(stream_id)
                except:
                    continue

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - int(bouquet_id1 * 65535)
                except:
                    continue

                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"
                bouquet_string = ""

                if self.playlist_info["playlist_type"] == "xtream":
                    extension = channel["container_extension"]
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/movie/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(extension) + ":" + str(name) + "\n"
                else:
                    source = quote(channel.get("source", ""))
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                self.vod_stream_data.append({
                    "category_id": str(category_id),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })

            if self.vod_stream_data:

                if cfg.groups.value and not self.bouquet_tv:
                    self.buildBouquetTvGroupedFile()

                bouquet_tv_string = ""

                if cfg.groups.value and not self.userbouquet:
                    bouquet_tv_string += "#NAME " + str(self.playlist_info["name"]) + "\n"

                bouquet_filename = ""

                # Create dictionary for faster category lookups (reduces repeated scans)
                cat_map = {}
                for stream in self.vod_stream_data:
                    cat_id = stream["category_id"]
                    if cat_id not in cat_map:
                        cat_map[cat_id] = []
                    cat_map[cat_id].append(stream)

                for category in self.vod_categories:
                    category_id = category.get("category_id")

                    if not category_id or str(category_id) in vod_categories_hidden or str(category_id) not in cat_map:
                        continue

                    if cfg.groups.value:
                        bouquet_filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    else:
                        bouquet_filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_vod_" + str(self.name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

                if bouquet_filename:
                    with open(bouquet_filename, "a+") as f:
                        f.write(str(bouquet_tv_string))

                    for category in self.vod_categories:
                        category_id = category.get("category_id")

                        if not category_id or str(category_id) in vod_categories_hidden or str(category_id) not in cat_map:
                            continue

                        bouquet_title = self.name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""

                        if self.settings["prefix_name"] and not cfg.groups.value:
                            output_string += "#NAME " + self.name + " VOD - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "VOD - " + category["category_name"] + "\n"

                        for stream in cat_map[str(category_id)]:
                            output_string += stream["bouquet_string"]

                        if cfg.groups.value:
                            bouquet_filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"
                        else:
                            bouquet_filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"

                        with open(bouquet_filename, "w+") as f:
                            f.write(output_string)

                # Free up memory once finished
                self.vod_categories = []
                self.vod_streams = []
                self.vod_stream_data = []
                cat_map.clear()

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)

        if self.playlist_info["playlist_type"] == "xtream":
            if self.settings["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadXtreamSeries)
            else:
                self.finished()
                return
        else:
            if self.settings["show_series"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()
                return

    def loadSeries(self):
        if debugs:
            print("*** loadSeries ***")

        if glob.current_playlist["settings"]["show_series"] and self.series_categories and self.series_streams:
            self.clearCaches()
            self.series_stream_data = []
            # stream_type = self.settings["vod_type"]

            if self.settings["vod_category_order"] == "alphabetical":
                self.series_categories.sort(key=lambda k: k["category_name"].lower())

            # Convert to sets for faster membership testing

            series_categories_hidden = set(self.data["series_categories_hidden"])

            for category in self.series_categories:
                category_id = category.get("category_id")
                name = category.get("category_name")

                if not category_id or not name or str(category_id) in series_categories_hidden:
                    continue

            self.progress_value += 1
            self["progress"].setValue(self.progress_value)

            if self.playlist_info["playlist_type"] == "xtream":
                geturl = str(self.host) + "/get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=m3u_plus&output=" + str(self.output)

                method, result = bmx.downloadM3U8File_with_fallback(geturl)

                if not result:
                    glob.get_series_failed = True
                    self.finished()
                    return

                if method == "curl":
                    print("*** streaming parse started (curl) ***")
                    self.nextJob(_("Parsing series data..."), lambda: self.parseXtreamSeries_streaming(result))
                elif method in ("wget", "requests"):
                    print("*** parsing non-streaming result ***")
                    self.series_streams = seriesparsem3u.parseM3u8Playlist(result)

                    result = None

                    self.nextJob(_("Processing series data..."), self.processSeries)
                else:
                    print("*** all methods failed ***")
                    self.finished()
            else:
                self.nextJob(_("Processing series data..."), self.processSeries)

    def parseXtreamSeries_streaming(self, pipe_process):
        if debugs:
            print("*** parseXtreamSeries_streaming ***")

        try:
            self.series_streams = seriesparsem3u.parseM3u8Playlist_streaming(pipe_process)
        finally:
            pipe_process.stdout.close()
            pipe_process.wait()  # Ensure curl finishes

        if not self.series_streams:
            self.finished()
            return

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing series data..."), self.processSeries)

    def processSeries(self):
        if debugs:
            print("*** processSeries ***")

        if self.settings["vod_stream_order"] == "alphabetical":
            self.series_streams.sort(key=lambda x: x["name"].lower())

        elif self.settings["vod_stream_order"] == "added":
            self.series_streams.sort(key=lambda x: x["added"], reverse=True)

        BATCH_SIZE = 20000
        stream_type = self.settings["vod_type"]

        def process_stream_batch(streams_batch):
            batch_data = []
            for channel in streams_batch:

                category_id = channel.get("category_id")
                name = channel.get("name") or ""
                name = name.replace(":", "").replace('"', "").replace('•', "-").strip("- ").strip()
                stream_id = channel.get("series_id")

                if not category_id or not name:
                    continue

                try:
                    stream_id = int(stream_id)
                except:
                    continue

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - int(bouquet_id1 * 65535)
                except:
                    continue

                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"
                bouquet_string = ""

                source = quote(channel.get("source", ""))
                bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                batch_data.append({
                    "category_id": str(category_id),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })
            return batch_data

        # Process all streams in manageable batches
        total_streams = len(self.series_streams)
        all_series_data = []

        for batch_start in range(0, total_streams, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_streams)
            batch = self.series_streams[batch_start:batch_end]
            batch_data = process_stream_batch(batch)
            all_series_data.extend(batch_data)

            # Clear memory between batches
            if batch_start % 200 == 0:  # Clear memory every 2 batches
                self.clearCaches()

        self.series_stream_data = all_series_data

        self.createSeriesBouquets()

    def createSeriesBouquets(self):
        if debugs:
            print("*** createSeriesBouquets ***")

        if not self.series_stream_data:
            self.finished()
            return

        if cfg.groups.value and not self.bouquet_tv:
            self.buildBouquetTvGroupedFile()

        bouquet_tv_string = ""

        if cfg.groups.value and not self.userbouquet:
            bouquet_tv_string += "#NAME " + str(self.playlist_info["name"]) + "\n"

        bouquet_filename = ""

        # Build dictionary for fast category lookups
        cat_map = {}
        for stream in self.series_stream_data:
            cat_id = str(stream["category_id"])
            if cat_id not in cat_map:
                cat_map[cat_id] = []
            cat_map[cat_id].append(stream)

        # Write top-level bouquet entries
        for category in self.series_categories:
            category_id = category.get("category_name")

            if not category_id:
                continue

            # Skip hidden or missing categories
            if str(category_id) in self.data["series_categories_hidden"] or str(category_id) not in cat_map:
                continue

            if cfg.groups.value:
                bouquet_filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.name) + ".tv"
                bouquet = "subbouquet"
                self.userbouquet = True
            else:
                bouquet_filename = "/etc/enigma2/bouquets.tv"
                bouquet = "userbouquet"

            bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_series_" + str(self.name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

        if bouquet_filename:
            with open(bouquet_filename, "a+") as f:
                f.write(str(bouquet_tv_string))

            category_batches = [self.series_categories[i:i + 10] for i in range(0, len(self.series_categories), 10)]

            for batch_num, category_batch in enumerate(category_batches):
                """
                if debugs:
                    print("[BMX] Creating series bouquet batch %d" % (batch_num + 1))
                    """

                for category in category_batch:
                    category_id = category.get("category_name")

                    if not category_id:
                        continue

                    if str(category_id) in self.data["series_categories_hidden"] or str(category_id) not in cat_map:
                        continue

                    bouquet_title = self.name + "_" + bmx.safeName(category["category_name"])
                    self.total_count += 1
                    output_string = ""

                    if self.settings["prefix_name"] and not cfg.groups.value:
                        output_string += "#NAME " + self.name + " Series - " + category["category_name"] + "\n"
                    else:
                        output_string += "#NAME " + "Series - " + category["category_name"] + "\n"

                    for stream in cat_map[str(category_id)]:
                        output_string += stream["bouquet_string"]

                    if cfg.groups.value:
                        filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"
                    else:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"

                    with open(filename, "w+") as f:
                        f.write(output_string)

        self.clearCaches()
        self.finished()

    def buildBouquetTvGroupedFile(self):
        if debugs:
            print("*** buildBouquetTvGroupedFile ***")
        exists = False
        groupname = "userbouquet.bouquetmakerxtream_" + str(self.name) + ".tv"
        with open("/etc/enigma2/bouquets.tv", "r") as f:
            for ln, line in enumerate(f):
                if str(groupname) in line:
                    exists = True
                    break

        if not exists:
            with open("/etc/enigma2/bouquets.tv", "a+") as f:
                bouquet_tv_string = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(groupname) + '" ORDER BY bouquet\n'
                f.write(str(bouquet_tv_string))

        self.bouquet_tv = True

    def buildXmltvSource(self):
        if debugs:
            print("*** buildXmltvSource ***")
        import xml.etree.ElementTree as ET

        file_path = "/etc/epgimport/"
        epg_filename = "bouquetmakerxtream." + str(self.name) + ".channels.xml"
        channel_path = os.path.join(file_path, epg_filename)
        source_file = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if not os.path.isfile(source_file) or os.stat(source_file).st_size == 0:
            with open(source_file, "w") as f:
                xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
                xml_str += "<sources>\n"
                xml_str += '<sourcecat sourcecatname="BouquetMakerXtream EPG">\n'
                xml_str += "</sourcecat>\n"
                xml_str += "</sources>\n"
                f.write(xml_str)

        try:
            tree = ET.parse(source_file, parser=ET.XMLParser(encoding="utf-8"))
            root = tree.getroot()
            sourcecat = root.find("sourcecat")

            for elem in root.iter():
                for child in list(elem):
                    description = ""
                    if child.tag == "source":
                        try:
                            description = child.find("description").text

                            if str(self.name) == str(description):
                                elem.remove(child)
                        except:
                            pass

            epg_offset = 0
            try:
                epg_offset = int(self.settings.get("epg_offset", 0))
            except:
                pass

            if epg_offset > 0:
                offset_str = "-{0:02d}00".format(epg_offset)
            elif epg_offset < 0:
                offset_str = "{0:02d}00".format(abs(epg_offset))
            else:
                offset_str = "0000"

            source = ET.SubElement(
                sourcecat,
                "source",
                type="gen_xmltv",
                nocheck="1",
                offset=offset_str,
                channels=channel_path
            )

            description = ET.SubElement(source, "description")
            description.text = str(self.name)

            url = ET.SubElement(source, "url")
            url.text = str(self.xmltv_api)

            tree.write(source_file)

        except Exception as e:
            print(e)

        try:
            with open(source_file, "r+") as f:
                xml_str = f.read()
                f.seek(0)
                doc = minidom.parseString(xml_str)
                xml_output = doc.toprettyxml(encoding="utf-8", indent="\t")
                try:
                    xml_output = os.linesep.join([s for s in xml_output.splitlines() if s.strip()])
                except:
                    xml_output = os.linesep.join([s for s in xml_output.decode().splitlines() if s.strip()])
                f.write(xml_output)
        except Exception as e:
            print(e)

        self.buildXmltvChannels()

    def buildXmltvChannels(self):
        if debugs:
            print("*** buildXmltvChannels ***")
        file_path = "/etc/epgimport/"
        epg_filename = "bouquetmakerxtream." + str(self.name) + ".channels.xml"
        channel_path = os.path.join(file_path, epg_filename)

        if not os.path.isfile(channel_path):
            open(channel_path, "a").close()

        with open(channel_path, "w") as f:
            xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
            xml_str += "<channels>\n"

            if self.live_stream_data:
                for stream in self.live_stream_data:
                    if stream["xml_str"] and stream["xml_str"] is not None:
                        xml_str += stream["xml_str"]
            xml_str += "</channels>\n"
            f.write(xml_str)

    def clearCaches(self):
        if debugs:
            print("*** clearCaches ***")
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def finished(self):
        if debugs:
            print("*** finished ***")

        self.updateJson()
        self.clearCaches()
        bmx.refreshBouquets()

        message = ""

        if getattr(glob, "get_series_failed", False):
            message += _("Series failed to download get.php file.\n\n")

        message += str(self.total_count) + _(" IPTV Bouquets Created")

        self.session.openWithCallback(
            self.exit,
            MessageBox,
            message,
            MessageBox.TYPE_INFO,
            timeout=10
        )

    def exit(self, answer=None):
        if debugs:
            print("*** exit ***")
        glob.finished = True
        self.close(True)

    def updateJson(self):
        if debugs:
            print("*** updateJson ***")
        if self.playlists_all:
            for index, playlists in enumerate(self.playlists_all):
                if playlists["playlist_info"]["full_url"] == self.playlist_info["full_url"]:
                    self.playlists_all[index]["playlist_info"]["bouquet"] = True
                    self.playlists_all[index]["data"]["live_categories"] = []
                    self.playlists_all[index]["data"]["vod_categories"] = []
                    self.playlists_all[index]["data"]["series_categories"] = []
                    self.playlists_all[index]["data"]["live_streams"] = []
                    self.playlists_all[index]["data"]["vod_streams"] = []
                    self.playlists_all[index]["data"]["series_streams"] = []
                    break

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f, indent=4)
