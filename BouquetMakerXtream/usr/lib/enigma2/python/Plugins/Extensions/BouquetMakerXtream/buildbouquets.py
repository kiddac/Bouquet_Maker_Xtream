#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import parsem3u
from . import seriesparsem3u
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .plugin import epgimporter, cfg, playlists_json, skin_directory, debugs

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

        settings = glob.current_playlist["settings"]
        playlist_info = glob.current_playlist["playlist_info"]

        if playlist_info == "xtream":
            self.progress_range += 2 * sum([
                settings["show_live"],
                settings["show_vod"],
                settings["show_series"]
            ])
        else:
            self.progress_range += 1  # Base range for non-xtream playlists
            self.progress_range += sum([
                settings["show_live"],
                settings["show_vod"],
                settings["show_series"]
            ])

        self.playlists_all = bmx.getPlaylistJson()

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

        playlist_info = glob.current_playlist["playlist_info"]

        self["progress"].setRange((0, self.progress_range))
        self["progress"].setValue(self.progress_value)
        self.safe_name = bmx.safeName(playlist_info["name"])
        self.old_name = bmx.safeName(glob.old_name)
        self.deleteExistingRefs()

    def deleteExistingRefs(self):
        if debugs:
            print("*** deleteExistingRefs ***")
        with open("/etc/enigma2/bouquets.tv", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            f.truncate()

            for line in lines:
                if "bouquetmakerxtream_live_" + str(self.safe_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(self.safe_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(self.safe_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(self.safe_name) + ".tv" in line:
                    continue
                if "bouquetmakerxtream_live_" + str(self.old_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(self.old_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(self.old_name) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(self.old_name) + ".tv" in line:
                    continue
                f.write(line)

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_" + str(self.safe_name))

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.old_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.old_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.old_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_" + str(self.old_name))

        if epgimporter:
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.safe_name))
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.old_name))

        self.makeUrlList()

    def makeUrlList(self):
        if debugs:
            print("*** makeUrlList ***")
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        settings = glob.current_playlist["settings"]
        playlist_info = glob.current_playlist["playlist_info"]

        full_url = playlist_info["full_url"]

        if playlist_info["playlist_type"] != "local":
            protocol = playlist_info["protocol"]
            domain = playlist_info["domain"]
            port = playlist_info["port"]

            self.host = protocol + domain + (":" + str(port) if port else "")

            self.host_encoded = quote(self.host)

            for j in str(full_url):
                value = ord(j)
                self.unique_ref += value

            if playlist_info["playlist_type"] == "xtream":
                player_api = str(playlist_info["player_api"])
                self.xmltv_api = str(playlist_info["xmltv_api"])
                try:
                    if "next_days" in settings and settings["next_days"] != "0":
                        self.xmltv_api = str(playlist_info["xmltv_api"]) + "&next_days=" + str(settings["next_days"])
                except:
                    pass

                self.username = playlist_info["username"]
                self.password = playlist_info["password"]
                self.output = playlist_info["output"]

                if settings["show_live"]:
                    self.live_url_list.append([player_api + "&action=get_live_streams", 3, "json"])

                if settings["show_vod"]:
                    self.vod_url_list.append([player_api + "&action=get_vod_streams", 4, "json"])

                if settings["show_series"]:
                    self.series_url_list.append([player_api + "&action=get_series", 5, "json"])
                    # self.simple = str(self.host) + "/get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=simple&output=" + str(self.output)

                if settings["show_live"]:
                    self.nextJob(_("Downloading live data..."), self.downloadLive)

                elif settings["show_vod"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                elif settings["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)

                else:
                    self.finished()

            elif playlist_info["playlist_type"] == "external":
                self.external_url_list.append([full_url, 6, "text"])
                self.nextJob(_("Downloading external playlist..."), self.downloadExternal)
        else:
            self.nextJob(_("Loading local playlist..."), self.loadLocal)

    def downloadLive(self):
        if debugs:
            print("*** downloadLive ***")
        self.processDownloads("live", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def downloadVod(self):
        if debugs:
            print("*** downloadVod ***")
        self.processDownloads("vod", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing VOD data..."), self.loadVod)

    def downloadSeries(self):
        if debugs:
            print("*** downloadSeries ***")
        self.processDownloads("series", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing series data..."), self.loadSeries)

    def downloadExternal(self):
        if debugs:
            print("*** downloadExternal ***")
        self.processDownloads("external", "text")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def loadLocal(self):
        if debugs:
            print("*** loadLocal ***")
        self.parseM3u8Playlist()

    def processDownloads(self, stream_type, outputtype=None):
        if debugs:
            print("*** processDownloads ***")

        playlist_info = glob.current_playlist["playlist_info"]

        if stream_type == "live":
            self.url_list = self.live_url_list

        elif stream_type == "vod":
            self.url_list = self.vod_url_list

        elif stream_type == "series":
            self.url_list = self.series_url_list

        elif stream_type == "external":
            self.url_list = self.external_url_list

        if outputtype == "json":
            output_file = ""
        else:
            output_file = '/var/volatile/tmp/bouquetmakerxtream/temp'

        for url in self.url_list:

            if outputtype == "json":
                result = bmx.downloadUrlCategory(url)
            else:
                result = bmx.downloadUrlMulti(url, output_file)

            category = result[0]
            response = ""

            if output_file and os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    response = f.read()
            else:
                response = result[1]

            if response:
                if playlist_info["playlist_type"] == "xtream":
                    if category == 3:
                        self.live_streams = response

                    elif category == 4:
                        self.vod_streams = response

                    elif category == 5:
                        self.series_streams = response
                else:
                    self.parseM3u8Playlist(response)

            # Delete the file after processing
            if os.path.exists(output_file):
                os.remove(output_file)

    def loadLive(self):
        if debugs:
            print("*** loadLive ***")

        self.clearCaches()

        self.live_stream_data = []
        settings = glob.current_playlist["settings"]
        playlist_info = glob.current_playlist["playlist_info"]
        data = glob.current_playlist["data"]

        stream_type = settings["live_type"]
        live_categories = data["live_categories"]

        if not live_categories:

            if playlist_info["playlist_type"] == "xtream":

                if settings["show_vod"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                elif settings["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)

                else:
                    self.finished()
                    return
            else:
                if settings["show_vod"]:
                    self.nextJob(_("Process VOD data..."), self.loadVod)
                elif settings["show_series"]:
                    self.nextJob(_("Processing series data..."), self.loadSeries)
                else:
                    self.finished()
                    return

        if playlist_info["playlist_type"] != "xtream":
            self.live_streams = data["live_streams"]

        if settings["live_category_order"] == "alphabetical":
            live_categories.sort(key=lambda k: k["category_name"].lower())

        if self.live_streams:
            for channel in self.live_streams:
                stream_id = str(channel["stream_id"])
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in data["live_categories_hidden"] or \
                   str(stream_id) in data["live_streams_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")
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

                if "custom_sid" in channel and channel["custom_sid"] and str(channel["custom_sid"]) not in ("null", "None", "0") and len(channel["custom_sid"]) > 16:
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

                if playlist_info["playlist_type"] == "xtream":
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/live/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(self.output) + ":" + str(name) + "\n"
                else:
                    source = quote(channel.get("source", ""))
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                bouquet_string += "#DESCRIPTION " + str(name) + "\n"

                self.live_stream_data.append({
                    "category_id": str(category_id),
                    "xml_str": str(xml_str),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })

        if self.live_stream_data:

            # Sort streams once (cached results)
            if settings["live_stream_order"] == "alphabetical":
                self.live_stream_data.sort(key=lambda x: x["name"].lower())
            elif settings["live_stream_order"] == "added":
                self.live_stream_data.sort(key=lambda x: x["added"], reverse=True)

            if cfg.groups.value and not self.bouquet_tv:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and not self.userbouquet:
                bouquet_tv_string += "#NAME " + str(playlist_info["name"]) + "\n"

            filename = ""

            for category in live_categories:
                category_id = category.get("category_id")
                if not category_id:
                    continue

                exists = any(item for item in self.live_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in data["live_categories_hidden"] and exists:
                    if cfg.groups.value:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    else:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_live_" + str(self.safe_name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            if filename:
                with open(filename, "a+") as f:
                    f.write(str(bouquet_tv_string))

                for category in live_categories:
                    category_id = category.get("category_id")

                    if not category_id:
                        continue

                    exists = any(item for item in self.live_stream_data if item.get("category_id") == category_id)

                    if str(category_id) not in data["live_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if settings["prefix_name"] and not cfg.groups.value:
                            output_string += "#NAME " + self.safe_name + " - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + category["category_name"] + "\n"

                        for stream in self.live_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        for string in string_list:
                            output_string += string[0]

                        if cfg.groups.value:
                            filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"
                        else:
                            filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"

                        with open(filename, "w+") as f:
                            f.write(output_string)

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)

        data["live_categories"] = []
        data["live_streams"] = []

        if playlist_info["playlist_type"] == "xtream":
            if live_categories and epgimporter:
                self.buildXmltvSource()

            if settings["show_vod"]:
                self.nextJob(_("Downloading VOD data..."), self.downloadVod)

            elif settings["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if settings["show_vod"]:
                self.nextJob(_("Process VOD data..."), self.loadVod)
            elif settings["show_series"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadVod(self):
        if debugs:
            print("*** loadVod ***")

        self.clearCaches()

        self.vod_stream_data = []

        settings = glob.current_playlist["settings"]
        playlist_info = glob.current_playlist["playlist_info"]
        data = glob.current_playlist["data"]

        stream_type = settings["vod_type"]
        vod_categories = data["vod_categories"]

        if not vod_categories:

            if playlist_info["playlist_type"] == "xtream":

                if settings["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)
                else:
                    self.finished()
                    return
            else:
                if settings["show_series"]:
                    self.nextJob(_("Processing series data..."), self.loadSeries)
                else:
                    self.finished()
                    return

        if playlist_info["playlist_type"] != "xtream":
            self.vod_streams = data["vod_streams"]

        if settings["vod_category_order"] == "alphabetical":
            vod_categories.sort(key=lambda k: k["category_name"].lower())

        if self.vod_streams:
            for channel in self.vod_streams:
                stream_id = str(channel["stream_id"])
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in data["vod_categories_hidden"] or \
                   str(stream_id) in data["vod_streams_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - int(bouquet_id1 * 65535)
                except:
                    continue

                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"
                bouquet_string = ""

                if playlist_info["playlist_type"] == "xtream":
                    extension = channel["container_extension"]
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/movie/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(extension) + ":" + str(name) + "\n"
                else:
                    source = quote(channel.get("source", ""))
                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                    bouquet_string += "#DESCRIPTION " + str(name) + "\n"

                self.vod_stream_data.append({
                    "category_id": str(category_id),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })

        if self.vod_stream_data:

            if settings["vod_stream_order"] == "alphabetical":
                self.vod_stream_data.sort(key=lambda x: x["name"].lower())
            elif settings["vod_stream_order"] == "added":
                self.vod_stream_data.sort(key=lambda x: x["added"], reverse=True)

            if cfg.groups.value and not self.bouquet_tv:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and not self.userbouquet:
                bouquet_tv_string += "#NAME " + str(playlist_info["name"]) + "\n"

            filename = ""

            for category in vod_categories:
                category_id = category.get("category_id")
                if not category_id:
                    continue

                exists = any(item for item in self.vod_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in data["vod_categories_hidden"] and exists:
                    if cfg.groups.value:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    else:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_vod_" + str(self.safe_name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            if filename:
                with open(filename, "a+") as f:
                    f.write(str(bouquet_tv_string))

                for category in vod_categories:
                    category_id = category.get("category_id")

                    if not category_id:
                        continue

                    exists = any(item for item in self.vod_stream_data if item.get("category_id") == category_id)

                    if str(category_id) not in data["vod_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if settings["prefix_name"] and not cfg.groups.value:
                            output_string += "#NAME " + self.safe_name + " VOD - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "VOD - " + category["category_name"] + "\n"

                        for stream in self.vod_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        for string in string_list:
                            output_string += string[0]

                        if cfg.groups.value:
                            filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"
                        else:
                            filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"

                        with open(filename, "w+") as f:
                            f.write(output_string)

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)

        data["vod_categories"] = []
        data["vod_streams"] = []

        if playlist_info["playlist_type"] == "xtream":
            if settings["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if settings["show_series"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadSeries(self):
        if debugs:
            print("*** loadSeries ***")

        self.clearCaches()

        self.series_stream_data = []

        settings = glob.current_playlist["settings"]
        playlist_info = glob.current_playlist["playlist_info"]
        data = glob.current_playlist["data"]

        stream_type = settings["vod_type"]
        series_categories = data["series_categories"]

        if not series_categories:
            self.finished()
            return

        if settings["vod_category_order"] == "alphabetical":
            series_categories.sort(key=lambda k: k["category_name"].lower())

        if playlist_info["playlist_type"] == "xtream":
            protocol = playlist_info["protocol"]
            domain = playlist_info["domain"]
            port = playlist_info["port"]

            self.host = protocol + domain + (":" + str(port) if port else "")

            self.username = playlist_info["username"]
            self.password = playlist_info["password"]
            self.output = playlist_info["output"]

            geturl = str(self.host) + "/get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=m3u_plus&output=" + str(self.output)

            response = bmx.downloadUrlMulti([geturl, 7, "text"])

            if response:
                self.seriesParseM3u8Playlist(response[1])

        self.series_streams = data["series_streams"]

        if self.series_streams:
            for channel in self.series_streams:
                stream_id = channel.get("series_id")
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in data["series_categories_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - int(bouquet_id1 * 65535)
                except:
                    continue

                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"
                bouquet_string = ""

                source = quote(channel.get("source", ""))
                bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"
                bouquet_string += "#DESCRIPTION " + str(name) + "\n"
                self.series_stream_data.append({
                    "category_id": str(category_id),
                    "bouquet_string": bouquet_string,
                    "name": str(name),
                    "added": str(channel.get("added", "0"))
                })

        if self.series_stream_data:

            if settings["vod_stream_order"] == "alphabetical":
                self.series_stream_data.sort(key=lambda x: x["name"].lower())
            elif settings["vod_stream_order"] == "added":
                self.series_stream_data.sort(key=lambda x: x["added"], reverse=True)

            if cfg.groups.value and not self.bouquet_tv:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and not self.userbouquet:
                bouquet_tv_string += "#NAME " + str(playlist_info["name"]) + "\n"

            filename = ""

            for category in series_categories:
                category_id = category.get("category_name")

                if not category_id:
                    continue

                exists = any(item for item in self.series_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in data["series_categories_hidden"] and exists:
                    if cfg.groups.value:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    else:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_series_" + str(self.safe_name) + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            if filename:
                with open(filename, "a+") as f:
                    f.write(str(bouquet_tv_string))

                for category in series_categories:
                    category_id = category.get("category_name")

                    if not category_id:
                        continue

                    exists = any(item for item in self.series_stream_data if item.get("category_id") == category_id)

                    if str(category_id) not in data["series_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if settings["prefix_name"] and not cfg.groups.value:
                            output_string += "#NAME " + self.safe_name + " Series - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "Series - " + category["category_name"] + "\n"

                        for stream in self.series_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        for string in string_list:
                            output_string += string[0]

                        if cfg.groups.value:
                            filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"
                        else:
                            filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"

                        with open(filename, "w+") as f:
                            f.write(output_string)

        self.progress_value += 1
        self["progress"].setValue(self.progress_value)

        data["series_categories"] = []
        data["series_streams"] = []

        self.finished()

    def parseM3u8Playlist(self, response=None):
        if debugs:
            print("*** parseM3u8Playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parseM3u8Playlist(response)
        self.makeM3u8CategoriesJson()

    def makeM3u8CategoriesJson(self):
        if debugs:
            print("*** makeM3u8CategoriesJson ***")
        parsem3u.makeM3u8CategoriesJson(self.live_streams, self.vod_streams, self.series_streams)
        self.makeM3u8StreamsJson()

    def makeM3u8StreamsJson(self):
        if debugs:
            print("*** makeM3u8StreamsJson ***")
        parsem3u.makeM3u8StreamsJson(self.live_streams, self.vod_streams, self.series_streams)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def seriesParseM3u8Playlist(self, response=None):
        if debugs:
            print("*** seriesParseM3u8Playlist ***")
        self.series_streams = seriesparsem3u.parseM3u8Playlist(response)
        return

    def buildBouquetTvGroupedFile(self):
        if debugs:
            print("*** buildBouquetTvGroupedFile ***")
        exists = False
        groupname = "userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
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
        epg_filename = "bouquetmakerxtream." + str(self.safe_name) + ".channels.xml"
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

                            if str(self.safe_name) == str(description):
                                elem.remove(child)
                        except:
                            pass

            source = ET.SubElement(sourcecat, "source", type="gen_xmltv", nocheck="1", channels=channel_path)
            description = ET.SubElement(source, "description")
            description.text = str(self.safe_name)

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
        epg_filename = "bouquetmakerxtream." + str(self.safe_name) + ".channels.xml"
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
        self.session.openWithCallback(self.exit, MessageBox, str(self.total_count) + _(" IPTV Bouquets Created"), MessageBox.TYPE_INFO, timeout=10)

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
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:
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
