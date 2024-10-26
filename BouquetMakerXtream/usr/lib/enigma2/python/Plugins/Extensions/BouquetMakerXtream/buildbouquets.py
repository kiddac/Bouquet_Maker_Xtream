#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import parsem3u
from . import seriesparsem3u
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .plugin import epgimporter, cfg, playlists_json, skin_directory

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

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            self.progress_range += 2 * sum([
                glob.current_playlist["settings"]["show_live"],
                glob.current_playlist["settings"]["show_vod"],
                glob.current_playlist["settings"]["show_series"]
            ])
        else:
            self.progress_range += 1  # Base range for non-xtream playlists
            self.progress_range += sum([
                glob.current_playlist["settings"]["show_live"],
                glob.current_playlist["settings"]["show_vod"],
                glob.current_playlist["settings"]["show_series"]
            ])

        self.playlists_all = bmx.getPlaylistJson()

        self.starttimer = eTimer()
        try:
            self.starttimer_conn = self.starttimer.timeout.connect(self.start)
        except:
            self.starttimer.callback.append(self.start)
        self.starttimer.start(100, True)

    def void(self):
        pass

    def nextJob(self, actiontext, function):
        self["action"].setText(actiontext)
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(function)
        except:
            self.timer.callback.append(function)
        self.timer.start(50, True)

    def start(self):
        self["progress"].setRange((0, self.progress_range))
        self["progress"].setValue(self.progress_value)
        self.safe_name = bmx.safeName(glob.current_playlist["playlist_info"]["name"])
        self.old_name = bmx.safeName(glob.old_name)
        self.deleteExistingRefs()

    def deleteExistingRefs(self):
        with open("/etc/enigma2/bouquets.tv", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            f.truncate()

            # Patterns to skip
            patterns_to_skip = [
                "bouquetmakerxtream_live_" + self.safe_name + "_",
                "bouquetmakerxtream_vod_" + self.safe_name + "_",
                "bouquetmakerxtream_series_" + self.safe_name + "_",
                "bouquetmakerxtream_" + self.safe_name + ".tv",
                "bouquetmakerxtream_live_" + self.old_name + "_",
                "bouquetmakerxtream_vod_" + self.old_name + "_",
                "bouquetmakerxtream_series_" + self.old_name + "_",
                "bouquetmakerxtream_" + self.old_name + ".tv"
            ]

            for line in lines:
                if any(pattern in line for pattern in patterns_to_skip):
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
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        full_url = glob.current_playlist["playlist_info"]["full_url"]

        if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
            protocol = glob.current_playlist["playlist_info"]["protocol"]
            domain = glob.current_playlist["playlist_info"]["domain"]
            port = glob.current_playlist["playlist_info"]["port"]

            if port:
                self.host = protocol + domain + ":" + str(port)
            else:
                self.host = protocol + domain

            self.host_encoded = quote(self.host)

            for j in str(full_url):
                value = ord(j)
                self.unique_ref += value

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                player_api = str(glob.current_playlist["playlist_info"]["player_api"])
                self.xmltv_api = str(glob.current_playlist["playlist_info"]["xmltv_api"])

                next_days = glob.current_playlist["settings"].get("next_days", "0")

                if next_days != "0":
                    self.xmltv_api += "&next_days=" + str(next_days)

                self.username = glob.current_playlist["playlist_info"]["username"]
                self.password = glob.current_playlist["playlist_info"]["password"]
                self.output = glob.current_playlist["playlist_info"]["output"]

                if glob.current_playlist["settings"]["show_live"]:
                    self.live_url_list.append([player_api + "&action=get_live_streams", 3, "json"])

                if glob.current_playlist["settings"]["show_vod"]:
                    self.vod_url_list.append([player_api + "&action=get_vod_streams", 4, "json"])

                if glob.current_playlist["settings"]["show_series"]:
                    self.series_url_list.append([player_api + "&action=get_series", 5, "json"])
                    # self.simple = str(self.host) + "/get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=simple&output=" + str(self.output)

                if glob.current_playlist["settings"]["show_live"]:
                    self.nextJob(_("Downloading live data..."), self.downloadLive)

                elif glob.current_playlist["settings"]["show_vod"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                elif glob.current_playlist["settings"]["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)

                else:
                    self.finished()

            elif glob.current_playlist["playlist_info"]["playlist_type"] == "external":
                self.external_url_list.append([full_url, 6, "text"])
                self.nextJob(_("Downloading external playlist..."), self.downloadExternal)
        else:
            self.nextJob(_("Loading local playlist..."), self.loadLocal)

    def downloadLive(self):
        self.processDownloads("live", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def downloadVod(self):
        self.processDownloads("vod", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing VOD data..."), self.loadVod)

    def downloadSeries(self):
        self.processDownloads("series", "json")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing series data..."), self.loadSeries)

    def downloadExternal(self):
        self.processDownloads("external", "text")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def loadLocal(self):
        self.parseM3u8Playlist()

    def processDownloads(self, stream_type, outputtype=None):
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
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
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
        self.live_stream_data = []
        stream_type = glob.current_playlist["settings"]["live_type"]
        live_categories = glob.current_playlist["data"]["live_categories"]

        if not live_categories or (len(live_categories) == len(glob.current_playlist["data"]["live_categories_hidden"])):

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":

                if glob.current_playlist["settings"]["show_vod"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                elif glob.current_playlist["settings"]["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)

                else:
                    self.finished()
                    return
            else:
                if glob.current_playlist["settings"]["show_vod"]:
                    self.nextJob(_("Process VOD data..."), self.loadVod)
                elif glob.current_playlist["settings"]["show_series"]:
                    self.nextJob(_("Processing series data..."), self.loadSeries)
                else:
                    self.finished()
                    return

        if glob.current_playlist["playlist_info"]["playlist_type"] != "xtream":
            self.live_streams = glob.current_playlist["data"]["live_streams"]

        if glob.current_playlist["settings"]["live_category_order"] == "alphabetical":
            live_categories.sort(key=lambda k: k["category_name"].lower())

        if self.live_streams:
            for channel in self.live_streams:
                stream_id = str(channel["stream_id"])
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in glob.current_playlist["data"]["live_categories_hidden"] or \
                   str(stream_id) in glob.current_playlist["data"]["live_streams_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")
                catchup = int(channel.get("tv_archive", 0))

                if cfg.catchup.value and catchup == 1:
                    name = str(cfg.catchup_prefix.value) + str(name)

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) % 65535
                except:
                    continue

                service_ref = "1:0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:http%3a//example.m3u8"
                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"

                if "custom_sid" in channel and channel["custom_sid"]:
                    if channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None and channel["custom_sid"] != "0":
                        if channel["custom_sid"][0].isdigit():
                            channel["custom_sid"] = channel["custom_sid"][1:]

                        service_ref = str(":".join(channel["custom_sid"].split(":")[:7])) + ":0:0:0:http%3a//example.m3u8"
                        custom_sid = channel["custom_sid"]

                xml_str = ""

                channel_id = channel.get("epg_channel_id")
                if channel_id:
                    channel_id = channel_id.replace("&", "&amp;")
                    xml_str = '\t<channel id="' + str(channel_id) + '">' + str(service_ref) + "</channel><!-- " + str(name) + " -->\n"

                bouquet_string = ""

                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
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
            if cfg.groups.value and self.bouquet_tv is False:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and self.userbouquet is False:
                bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            filename = ""

            for category in live_categories:
                category_id = category.get("category_id")
                if not category_id:
                    continue

                exists = any(item for item in self.live_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in glob.current_playlist["data"]["live_categories_hidden"] and exists:
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

                    if str(category_id) not in glob.current_playlist["data"]["live_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if glob.current_playlist["settings"]["prefix_name"] and cfg.groups.value is False:
                            output_string += "#NAME " + self.safe_name + " - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + category["category_name"] + "\n"

                        for stream in self.live_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        if glob.current_playlist["settings"]["live_stream_order"] == "alphabetical":
                            string_list.sort(key=lambda x: x[1].lower())

                        if glob.current_playlist["settings"]["live_stream_order"] == "added":
                            string_list.sort(key=lambda x: x[2].lower(), reverse=True)

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

        glob.current_playlist["data"]["live_categories"] = []
        glob.current_playlist["data"]["live_streams"] = []

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if live_categories and epgimporter:
                self.buildXmltvSource()

            if glob.current_playlist["settings"]["show_vod"]:
                self.nextJob(_("Downloading VOD data..."), self.downloadVod)

            elif glob.current_playlist["settings"]["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if glob.current_playlist["settings"]["show_vod"]:
                self.nextJob(_("Process VOD data..."), self.loadVod)
            elif glob.current_playlist["settings"]["show_series"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadVod(self):
        self.vod_stream_data = []
        stream_type = glob.current_playlist["settings"]["vod_type"]
        vod_categories = glob.current_playlist["data"]["vod_categories"]

        if not vod_categories or (len(vod_categories) == len(glob.current_playlist["data"]["vod_categories_hidden"])):

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":

                if glob.current_playlist["settings"]["show_series"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)
                else:
                    self.finished()
                    return
            else:
                if glob.current_playlist["settings"]["show_series"]:
                    self.nextJob(_("Processing series data..."), self.loadSeries)
                else:
                    self.finished()
                    return

        if glob.current_playlist["playlist_info"]["playlist_type"] != "xtream":
            self.vod_streams = glob.current_playlist["data"]["vod_streams"]

        if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
            vod_categories.sort(key=lambda k: k["category_name"].lower())

        if self.vod_streams:
            for channel in self.vod_streams:
                stream_id = str(channel["stream_id"])
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in glob.current_playlist["data"]["vod_categories_hidden"] or \
                   str(stream_id) in glob.current_playlist["data"]["vod_streams_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) % 65535
                except:
                    continue

                custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"
                bouquet_string = ""

                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
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
            if cfg.groups.value and self.bouquet_tv is False:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and self.userbouquet is False:
                bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            filename = ""

            for category in vod_categories:
                category_id = category.get("category_id")
                if not category_id:
                    continue

                exists = any(item for item in self.vod_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in glob.current_playlist["data"]["vod_categories_hidden"] and exists:
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

                    if str(category_id) not in glob.current_playlist["data"]["vod_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if glob.current_playlist["settings"]["prefix_name"] and cfg.groups.value is False:
                            output_string += "#NAME " + self.safe_name + " VOD - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "VOD - " + category["category_name"] + "\n"

                        for stream in self.vod_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                            string_list.sort(key=lambda x: x[1].lower())

                        if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                            string_list.sort(key=lambda x: x[2].lower(), reverse=True)

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

        glob.current_playlist["data"]["vod_categories"] = []
        glob.current_playlist["data"]["vod_streams"] = []

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if glob.current_playlist["settings"]["show_series"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if glob.current_playlist["settings"]["show_series"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadSeries(self):
        self.series_stream_data = []
        stream_type = glob.current_playlist["settings"]["vod_type"]
        series_categories = glob.current_playlist["data"]["series_categories"]

        if not series_categories or (len(series_categories) == len(glob.current_playlist["data"]["series_categories_hidden"])):
            self.finished()
            return

        if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
            series_categories.sort(key=lambda k: k["category_name"].lower())

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            protocol = glob.current_playlist["playlist_info"]["protocol"]
            domain = glob.current_playlist["playlist_info"]["domain"]
            port = glob.current_playlist["playlist_info"]["port"]

            if port:
                self.host = protocol + domain + ":" + str(port)
            else:
                self.host = protocol + domain

            self.username = glob.current_playlist["playlist_info"]["username"]
            self.password = glob.current_playlist["playlist_info"]["password"]
            self.output = glob.current_playlist["playlist_info"]["output"]

            geturl = str(self.host) + "/get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=m3u_plus&output=" + str(self.output)

            # Directly use the URL in the download function
            output_file = '/var/volatile/tmp/bouquetmakerxtream/temp'

            result = bmx.downloadUrlMulti([geturl, 7, "text"], output_file)

            category = result[0]
            response = ""

            with open(output_file, 'r') as f:
                response = f.read()

            if response:
                self.seriesParseM3u8Playlist(response)

            # Delete the file after processing

            if os.path.exists(output_file):
                os.remove(output_file)

        self.series_streams = glob.current_playlist["data"]["series_streams"]

        if self.series_streams:
            for channel in self.series_streams:
                stream_id = channel.get("series_id")
                category_id = channel.get("category_id")

                if not stream_id or not category_id:
                    continue

                if str(category_id) in glob.current_playlist["data"]["series_categories_hidden"]:
                    continue

                if "name" not in channel or not channel["name"]:
                    continue

                name = channel["name"].replace(":", "").replace('"', "").strip("-")

                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) % 65535
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
            if cfg.groups.value and self.bouquet_tv is False:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value and self.userbouquet is False:
                bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            filename = ""

            for category in series_categories:
                category_id = category.get("category_name")

                if not category_id:
                    continue

                exists = any(item for item in self.series_stream_data if item.get("category_id") == category_id)

                if str(category_id) not in glob.current_playlist["data"]["series_categories_hidden"] and exists:
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

                    if str(category_id) not in glob.current_playlist["data"]["series_categories_hidden"] and exists:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if glob.current_playlist["settings"]["prefix_name"] and cfg.groups.value is False:
                            output_string += "#NAME " + self.safe_name + " Series - " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "Series - " + category["category_name"] + "\n"

                        for stream in self.series_stream_data:
                            if str(category_id) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                            string_list.sort(key=lambda x: x[1].lower())

                        if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                            string_list.sort(key=lambda x: x[2].lower(), reverse=True)

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

        glob.current_playlist["data"]["series_categories"] = []
        glob.current_playlist["data"]["series_streams"] = []

        self.finished()

    def parseM3u8Playlist(self, response=None):
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parseM3u8Playlist(response)
        self.makeM3u8CategoriesJson()

    def makeM3u8CategoriesJson(self):
        parsem3u.makeM3u8CategoriesJson(self.live_streams, self.vod_streams, self.series_streams)
        self.makeM3u8StreamsJson()

    def makeM3u8StreamsJson(self):
        parsem3u.makeM3u8StreamsJson(self.live_streams, self.vod_streams, self.series_streams)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def seriesParseM3u8Playlist(self, response=None):
        self.series_streams = seriesparsem3u.parseM3u8Playlist(response)
        return

    def buildBouquetTvGroupedFile(self):
        exists = False
        groupname = "userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
        with open("/etc/enigma2/bouquets.tv", "r") as f:
            for ln, line in enumerate(f):
                if str(groupname) in line:
                    exists = True
                    break

        if exists is False:
            with open("/etc/enigma2/bouquets.tv", "a+") as f:
                bouquet_tv_string = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(groupname) + '" ORDER BY bouquet\n'
                f.write(str(bouquet_tv_string))

        self.bouquet_tv = True

    def buildXmltvSource(self):
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
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def finished(self):
        self.updateJson()
        self.clearCaches()
        bmx.refreshBouquets()
        self.session.openWithCallback(self.exit, MessageBox, str(self.total_count) + _(" IPTV Bouquets Created"), MessageBox.TYPE_INFO, timeout=10)

    def exit(self, answer=None):
        glob.finished = True
        self.close(True)

    def updateJson(self):
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
            json.dump(self.playlists_all, f)
