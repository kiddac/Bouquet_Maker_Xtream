#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . import _
from . import parsem3u
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .plugin import epgimporter, screenwidth, cfg, playlists_json, pythonVer, skin_directory


try:
    from urllib import quote
except:
    from urllib.parse import quote

try:
    from xml.dom import minidom
except:
    pass


class BmxUpdate(Screen):
    def __init__(self, session, runtype):
        Screen.__init__(self, session)
        self.session = session
        self.runtype = runtype

        if self.runtype == "manual":
            skin_path = os.path.join(skin_directory, cfg.skin.getValue())
            skin = os.path.join(skin_path, "progress.xml")
            with open(skin, "r") as f:
                self.skin = f.read()
        else:
            skin = """
                <screen name="Updater" position="0,0" size="1920,1080" backgroundColor="#ff000000" flags="wfNoBorder">
                    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/icons/plugin-icon.png" position="30,25" size="150,60" alphatest="blend" zPosition="4"  />
                    <eLabel position="180,30" size="360,50" backgroundColor="#10232323" transparent="0" zPosition="-1"/>
                    <widget name="status" position="210,30" size="300,50" font="Regular;24" foregroundColor="#ffffff" backgroundColor="#000000" valign="center" noWrap="1" transparent="1" zPosition="5" />
                </screen>"""

            if screenwidth.width() <= 1280:
                skin = """
                    <screen name="Updater" position="0,0" size="1280,720" backgroundColor="#ff000000" flags="wfNoBorder">
                        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/icons/plugin-icon_sd.png" position="20,16" size="100,40" alphatest="blend" zPosition="4" />
                        <eLabel position="120,20" size="240,32" backgroundColor="#10232323" transparent="0" zPosition="-1"/>
                        <widget name="status" position="140,20" size="200,32" font="Regular;16" foregroundColor="#ffffff" backgroundColor="#000000" valign="center" noWrap="1" transparent="1" zPosition="5" />
                    </screen>"""

            self.skin = skin

        self.setup_title = _("Building Bouquets")

        self.categories = []
        self["action"] = Label(_("Building Bouquets..."))
        self["status"] = Label("")
        self["progress"] = ProgressBar()

        self.bouq = 0

        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            self.bouquets = [item for item in self.playlists_all if item["playlist_info"]["bouquet"] is True]
            self.bouquets_len = len(self.bouquets)

        self.looptimer = eTimer()
        try:
            self.looptimer_conn = self.looptimer.timeout.connect(self.bouquetLoop)
        except:
            self.looptimer.callback.append(self.bouquetLoop)
        self.looptimer.start(100, True)

    def loopPlaylists(self):
        if self.bouq < self.bouquets_len:
            self.bouquetLoop()
        else:
            if self.runtype == "manual":
                self.session.openWithCallback(self.done, MessageBox, str(len(self.bouquets)) + _(" Providers IPTV Updated"), MessageBox.TYPE_INFO, timeout=5)
            else:
                self.done()

    def bouquetLoop(self):
        # print("*** bouquetLoop ***", self.bouq)

        glob.current_playlist = self.bouquets[self.bouq]

        self.bouquet_tv = False
        self.userbouquet = False

        self.total_count = 0

        self.unique_ref = 0

        self.progress_value = 0
        self.progress_range = 0

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if glob.current_playlist["settings"]["show_live"] is True and glob.current_playlist["data"]["live_categories"]:
                self.progress_range += 2

            if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                self.progress_range += 2

            if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.progress_range += 2

        else:
            self.progress_range += 1

            if glob.current_playlist["settings"]["show_live"] is True and glob.current_playlist["data"]["live_categories"]:
                self.progress_range += 1

            if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                self.progress_range += 1

            if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.progress_range += 1

        self.start()

    def nextJob(self, actiontext, function):
        self["action"].setText(actiontext)
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(function)
        except:
            self.timer.callback.append(function)
        self.timer.start(50, True)

    def start(self):
        # print("*** start ***")
        self["progress"].setRange((0, self.progress_range))
        self["progress"].setValue(self.progress_value)
        self.safe_name = bmx.safeName(glob.current_playlist["playlist_info"]["name"])
        self["status"].setText(_("Updating Playlist %d of %d") % (self.bouq + 1, self.bouquets_len))
        self.deleteExistingRefs()

    def deleteExistingRefs(self):
        # print("*** deleteExistingRefs ***")

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
                f.write(line)

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.safe_name) + "_")
        bmx.purge("/etc/enigma2", str(self.safe_name) + str(".tv"))

        if epgimporter is True:
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.safe_name))

        self.makeUrlList()

    def makeUrlList(self):
        # print("*** makeUrlList ***")
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
                self.username = glob.current_playlist["playlist_info"]["username"]
                self.password = glob.current_playlist["playlist_info"]["password"]
                self.output = glob.current_playlist["playlist_info"]["output"]

                if glob.current_playlist["settings"]["show_live"] is True and glob.current_playlist["data"]["live_categories"]:
                    p_live_streams_url = player_api + "&action=get_live_streams"
                    self.live_url_list.append([p_live_streams_url, 3, "json"])

                if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                    p_vod_streams_url = player_api + "&action=get_vod_streams"
                    self.vod_url_list.append([p_vod_streams_url, 4, "json"])

                if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                    p_series_streams_url = player_api + "&action=get_series"
                    self.series_url_list.append([p_series_streams_url, 5, "json"])
                    self.simple = str(self.host) + "/" + "get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=simple&output=" + str(self.output)

                if glob.current_playlist["settings"]["show_live"] is True and glob.current_playlist["data"]["live_categories"]:
                    self.nextJob(_("Downloading live data..."), self.downloadLive)

                elif glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                    self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                elif glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                    self.nextJob(_("Downloading series data..."), self.downloadSeries)

                else:
                    self.finished()

            elif glob.current_playlist["playlist_info"]["playlist_type"] == "external":
                self.external_url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6, "text"])
                self.nextJob(_("Downloading external playlist..."), self.downloadExternal)
            else:
                self.nextJob(_("Loadind local playlist..."), self.loadLocal)

    def downloadLive(self):
        self.processDownloads("live")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def downloadVod(self):
        self.processDownloads("vod")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing VOD data..."), self.loadVod)

    def downloadSeries(self):
        self.processDownloads("series")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing series data..."), self.loadSeries)

    def downloadExternal(self):
        self.processDownloads("external")
        self.progress_value += 1
        self["progress"].setValue(self.progress_value)
        self.nextJob(_("Processing live data..."), self.loadLive)

    def loadLocal(self):
        self.parseM3u8Playlist()

    def processDownloads(self, stream_type):
        # print("*** processDownloads ***")

        if stream_type == "live":
            self.url_list = self.live_url_list

        if stream_type == "vod":
            self.url_list = self.vod_url_list

        if stream_type == "series":
            self.url_list = self.series_url_list

        if stream_type == "external":
            self.url_list = self.external_url_list

        for url in self.url_list:
            result = bmx.downloadUrlMulti(url)
            category = result[0]
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

    def loadLive(self):
        # print("*** loadLive ***")
        self.live_stream_data = []
        stream_list = []
        stream_type = glob.current_playlist["settings"]["live_type"]

        live_categories = glob.current_playlist["data"]["live_categories"]

        if live_categories:
            # self.live_streams = glob.current_playlist["data"]["live_streams"]

            if glob.current_playlist["settings"]["live_category_order"] == "alphabetical":
                live_categories = sorted(live_categories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["live_categories"]) == len(glob.current_playlist["data"]["live_categories_hidden"]):
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                        self.nextJob(_("Downloading VOD data..."), self.downloadVod)

                    elif glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                        self.nextJob(_("Downloading series data..."), self.downloadSeries)
                    else:
                        self.finished()
                else:
                    if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                        self.nextJob(_("Process VOD data..."), self.loadVod)
                    elif glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                        self.nextJob(_("Processing series data..."), self.loadSeries)
                    else:
                        self.finished()

        if live_categories and self.live_streams:
            x = 0
            for channel in self.live_streams:
                if x > 10000:
                    break

                stream_id = str(channel["stream_id"])

                if str(channel["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["live_streams_hidden"]:
                    name = channel["name"]
                    name = name.replace(":", "").replace('"', "").strip("-")

                    if "tv_archive" in channel:
                        catchup = int(channel["tv_archive"])
                    else:
                        catchup = 0

                    if cfg.catchup.value is True and catchup == 1:
                        name = str(cfg.catchup_prefix.value) + str(name)

                    channel_id = str(channel["epg_channel_id"])
                    if channel_id and "&" in channel_id:
                        channel_id = channel_id.replace("&", "&amp;")

                    bouquet_id1 = 0
                    calc_remainder = int(stream_id) // 65535
                    bouquet_id1 = bouquet_id1 + calc_remainder
                    bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                    service_ref = "1:0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:" + "http%3a//example.m3u8"
                    custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                    if "custom_sid" in channel:
                        if channel["custom_sid"] and channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None and channel["custom_sid"] != "0":
                            if channel["custom_sid"][0].isdigit():
                                channel["custom_sid"] = channel["custom_sid"][1:]

                            service_ref = str(":".join(channel["custom_sid"].split(":")[:7])) + ":0:0:0:" + "http%3a//example.m3u8"
                            custom_sid = channel["custom_sid"]

                    xml_str = ""
                    if channel_id and channel_id != "None":
                        xml_str = '\t<channel id="' + str(channel_id) + '">' + str(service_ref) + "</channel><!-- " + str(name) + " -->\n"

                    bouquet_string = ""

                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/live/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(self.output) + ":" + str(name) + "\n"
                    else:
                        source = str(channel["source"])
                        source = quote(source)
                        bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                    bouquet_string += "#DESCRIPTION " + str(name) + "\n"

                    stream_list.append({"category_id": str(channel["category_id"]), "xml_str": str(xml_str), "bouquet_string": bouquet_string, "name": str(channel["name"]), "added": str(channel["added"])})
                    x += 1

        self.live_stream_data = stream_list

        if self.live_stream_data:
            if cfg.groups.value is True and self.bouquet_tv is False:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""

            if cfg.groups.value is True and self.userbouquet is False:
                bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            for category in live_categories:
                exists = False
                for item in stream_list:
                    if category["category_id"] == item["category_id"]:
                        exists = True
                        break

                if (str(category["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"]) and exists is True:
                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    if cfg.groups.value is False:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_live_" + self.safe_name + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            with open(filename, "a+") as f:
                f.write(str(bouquet_tv_string))

            for category in live_categories:
                exists = False
                for item in stream_list:
                    if category["category_id"] == item["category_id"]:
                        exists = True
                        break

                if (str(category["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"]) and exists is True:
                    bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                    self.total_count += 1
                    output_string = ""
                    string_list = []

                    if glob.current_playlist["settings"]["prefix_name"] is True and cfg.groups.value is False:
                        output_string += "#NAME " + self.safe_name + "-Live | " + category["category_name"] + "\n"
                    else:
                        output_string += "#NAME " + "Live | " + category["category_name"] + "\n"

                    for stream in self.live_stream_data:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                    if glob.current_playlist["settings"]["live_stream_order"] == "alphabetical":
                        string_list.sort(key=lambda x: x[1].lower())

                    if glob.current_playlist["settings"]["live_stream_order"] == "added":
                        string_list.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in string_list:
                        output_string += string[0]

                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"

                    else:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_live_" + str(bouquet_title) + ".tv"

                    with open(filename, "w+") as f:
                        f.write(output_string)

        if live_categories:
            self.progress_value += 1
            self["progress"].setValue(self.progress_value)

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if live_categories:
                self.buildXmltvSource()

            if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                self.nextJob(_("Downloading VOD data..."), self.downloadVod)

            elif glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if glob.current_playlist["settings"]["show_vod"] is True and glob.current_playlist["data"]["vod_categories"]:
                self.nextJob(_("Process VOD data..."), self.loadVod)
            elif glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadVod(self):
        # print("*** loadVod ***")

        self.vod_stream_data = []
        stream_list = []
        stream_type = glob.current_playlist["settings"]["vod_type"]

        vod_categories = glob.current_playlist["data"]["vod_categories"]

        if vod_categories:
            # self.vod_streams = glob.current_playlist["data"]["vod_streams"]

            if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
                vod_categories = sorted(vod_categories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["vod_categories"]) == len(glob.current_playlist["data"]["vod_categories_hidden"]):
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                        self.nextJob(_("Downloading series data..."), self.downloadSeries)
                    else:
                        self.finished()
                else:
                    if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                        self.nextJob(_("Processing series data..."), self.loadSeries)
                    else:
                        self.finished()

        if vod_categories and self.vod_streams:
            x = 0
            for channel in self.vod_streams:
                if x > 5000:
                    break

                stream_id = str(channel["stream_id"])

                if str(channel["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["vod_streams_hidden"]:
                    extension = channel["container_extension"]

                    name = channel["name"]
                    name = name.replace(":", "").replace('"', "").strip("-")

                    bouquet_id1 = 0
                    calc_remainder = int(stream_id) // 65535
                    bouquet_id1 = bouquet_id1 + calc_remainder
                    bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                    custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                    bouquet_string = ""

                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(self.host_encoded) + "/movie/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(extension) + ":" + str(name) + "\n"
                    else:
                        source = str(channel["source"])
                        source = quote(source)
                        bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                    bouquet_string += "#DESCRIPTION " + str(name) + "\n"

                    stream_list.append({"category_id": str(channel["category_id"]), "bouquet_string": bouquet_string, "name": str(channel["name"]), "added": str(channel["added"])})
                    x += 1

        self.vod_stream_data = stream_list

        if self.vod_stream_data:
            if cfg.groups.value is True and self.bouquet_tv is False:
                self.buildBouquetTvGroupedFile()

            bouquet_tv_string = ""
            if cfg.groups.value is True and self.userbouquet is False:
                bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            for category in vod_categories:
                exists = False
                for item in stream_list:
                    if category["category_id"] == item["category_id"]:
                        exists = True
                        break

                if (str(category["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"]) and exists is True:
                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    if cfg.groups.value is False:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_vod_" + self.safe_name + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            with open(filename, "a+") as f:
                f.write(str(bouquet_tv_string))

            for category in vod_categories:
                exists = False
                for item in stream_list:
                    if category["category_id"] == item["category_id"]:
                        exists = True
                        break

                if (str(category["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"]) and exists is True:
                    bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                    self.total_count += 1
                    output_string = ""
                    string_list = []

                    if glob.current_playlist["settings"]["prefix_name"] is True and cfg.groups.value is False:
                        output_string += "#NAME " + self.safe_name + "-VOD | " + category["category_name"] + "\n"
                    else:
                        output_string += "#NAME " + "VOD | " + category["category_name"] + "\n"

                    for stream in self.vod_stream_data:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                    if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                        string_list.sort(key=lambda x: x[1].lower())

                    if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                        string_list.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in string_list:
                        output_string += string[0]

                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"
                    else:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_vod_" + str(bouquet_title) + ".tv"

                    with open(filename, "w+") as f:
                        f.write(output_string)

        if vod_categories:
            self.progress_value += 1
            self["progress"].setValue(self.progress_value)

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.nextJob(_("Downloading series data..."), self.downloadSeries)
            else:
                self.finished()
        else:
            if glob.current_playlist["settings"]["show_series"] is True and glob.current_playlist["data"]["series_categories"]:
                self.nextJob(_("Processing series data..."), self.loadSeries)
            else:
                self.finished()

    def loadSeries(self):
        # print("*** loadSeries ***")
        self.series_stream_data = []
        stream_list = []
        stream_type = glob.current_playlist["settings"]["vod_type"]
        series_simple_result = []

        series_categories = glob.current_playlist["data"]["series_categories"]

        if series_categories:
            # self.series_streams = glob.current_playlist["data"]["series_streams"]

            if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
                series_categories = sorted(series_categories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["series_categories"]) == len(glob.current_playlist["data"]["series_categories_hidden"]):
                self.finished()

        if series_categories and self.series_streams:
            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                url = str(self.simple)
                series_simple_result = bmx.downloadUrl(url, "text")

                if series_simple_result:
                    if "#EXTM3U" in str(series_simple_result):
                        self.session.open(MessageBox, _("Your provider does not have the 'simple' API call\nUnable to build series.\nAlternative method might be added in the future."), MessageBox.TYPE_INFO, timeout=10)
                        return stream_list

                    lines = series_simple_result.splitlines()

                    if pythonVer == 3:
                        lines = [x for x in lines if "/series/" in x.decode() or "/S01/" in x.decode() or "/E01" in x.decode() and "/live" not in x.decode() and "/movie/" not in x.decode()]
                    else:
                        lines = [x for x in lines if "/series/" in x or "/S01/" in x or "/E01" in x and "/live" not in x and "/movie/" not in x]

                    build_list = [x for x in self.series_streams if str(x["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"] and str(x["series_id"]) not in glob.current_playlist["data"]["series_streams_hidden"]]

                    if build_list:
                        try:
                            x = 0
                            for line in lines:
                                if pythonVer == 3:
                                    line = line.decode()

                                if x > 1000:
                                    break

                                series_url = line.split(" ")[0]
                                series_name = line.split(":")[-1].strip()
                                series_name = series_name.replace(":", "").replace('"', "").strip("-")
                                series_stream_id = series_url.split("/")[-1].split(".")[0]

                                name = ""
                                channel = []

                                for channel in build_list:
                                    if channel["name"] in series_name:
                                        name = channel["name"]
                                        name = name.replace(":", "").replace('"', "").strip("-")
                                        break

                                if name:
                                    bouquet_id1 = 0
                                    calc_remainder = int(series_stream_id) // 65535
                                    bouquet_id1 = bouquet_id1 + calc_remainder
                                    bouquet_id2 = int(series_stream_id) - int(calc_remainder * 65535)

                                    custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"
                                    bouquet_string = ""
                                    bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + quote(series_url) + ":" + str(series_name) + "\n"
                                    bouquet_string += "#DESCRIPTION " + str(series_name) + "\n"
                                    stream_list.append({"category_id": str(channel["category_id"]), "stream_id": str(series_stream_id), "bouquet_string": bouquet_string, "name": str(channel["name"]), "added": str(channel["last_modified"])})
                                    x += 1
                        except Exception as e:
                            print(e)

            else:
                for channel in self.series_streams:
                    stream_id = str(channel["series_id"])

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"] and str(channel["series_id"]) not in glob.current_playlist["data"]["series_streams_hidden"]:
                        name = channel["name"]
                        name = name.replace(":", "").replace('"', "").strip("-")

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                        bouquet_string = ""

                        source = str(channel["source"])
                        source = quote(source)
                        bouquet_string += "#SERVICE " + str(stream_type) + str(custom_sid) + str(source) + ":" + str(name) + "\n"
                        bouquet_string += "#DESCRIPTION " + str(name) + "\n"

                        stream_list.append({"category_id": str(channel["category_id"]), "bouquet_string": bouquet_string, "name": str(channel["name"]), "added": str(channel["added"])})

            self.series_stream_data = stream_list

            if self.series_stream_data:
                if cfg.groups.value is True and self.bouquet_tv is False:
                    self.buildBouquetTvGroupedFile()

                bouquet_tv_string = ""

                if cfg.groups.value is True and self.userbouquet is False:
                    bouquet_tv_string += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

                for category in series_categories:
                    exists = False
                    for item in stream_list:
                        if category["category_id"] == item["category_id"]:
                            exists = True
                            break

                    if (str(category["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"]) and exists is True:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        if cfg.groups.value is True:
                            filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safe_name) + ".tv"
                            bouquet = "subbouquet"
                            self.userbouquet = True
                        if cfg.groups.value is False:
                            filename = "/etc/enigma2/bouquets.tv"
                            bouquet = "userbouquet"

                        bouquet_tv_string += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_series_" + self.safe_name + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

                with open(filename, "a+") as f:
                    f.write(bouquet_tv_string)

                for category in series_categories:
                    exists = False
                    for item in stream_list:
                        if category["category_id"] == item["category_id"]:
                            exists = True
                            break

                    if (str(category["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"]) and exists is True:
                        bouquet_title = self.safe_name + "_" + bmx.safeName(category["category_name"])
                        self.total_count += 1
                        output_string = ""
                        string_list = []

                        if glob.current_playlist["settings"]["prefix_name"] is True and cfg.groups.value is False:
                            output_string += "#NAME " + self.safe_name + "-Series | " + category["category_name"] + "\n"
                        else:
                            output_string += "#NAME " + "Series | " + category["category_name"] + "\n"

                        for stream in self.series_stream_data:
                            if str(category["category_id"]) == str(stream["category_id"]):
                                string_list.append([str(stream["bouquet_string"]), str(stream["name"]), str(stream["added"])])

                        if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                            string_list.sort(key=lambda x: x[1].lower())

                        if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                            string_list.sort(key=lambda x: x[2].lower(), reverse=True)

                        for string in string_list:
                            output_string += string[0]

                        if cfg.groups.value is True:
                            filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"
                        else:
                            filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_series_" + str(bouquet_title) + ".tv"

                        with open(filename, "w+") as f:
                            f.write(output_string)
        if series_categories:
            self.progress_value += 1
            self["progress"].setValue(self.progress_value)

        self.finished()

    def parseM3u8Playlist(self, response=None):
        # print("*** parseM3u8Playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parseM3u8Playlist(response)
        self.makeM3u8CategoriesJson()

    def makeM3u8CategoriesJson(self):
        # print("*** makeM3u8CategoriesJson  ***")
        parsem3u.makeM3u8CategoriesJson(self.live_streams, self.vod_streams, self.series_streams)
        self.makeM3u8StreamsJson()

    def makeM3u8StreamsJson(self):
        # print("*** makeM3u8StreamsJson ***")
        parsem3u.makeM3u8StreamsJson(self.live_streams, self.vod_streams, self.series_streams)

    def buildBouquetTvGroupedFile(self):
        # print("*** buildBouquetTvGroupedFile ***")
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
        # print("*** buildXmltvSource ***")

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

        tree = ET.parse(source_file)
        root = tree.getroot()
        sourcecat = root.find("sourcecat")

        exists = False

        for sourceitem in sourcecat:
            if channel_path in sourceitem.attrib["channels"]:
                exists = True
                break

        if exists is False:
            source = ET.SubElement(sourcecat, "source", type="gen_xmltv", nocheck="1", channels=channel_path)
            description = ET.SubElement(source, "description")
            description.text = str(self.safe_name)

            url = ET.SubElement(source, "url")
            url.text = str(self.xmltv_api)

            tree.write(source_file)

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
        # print("*** build_xmltv channels ***")

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

    def finished(self):
        # print("**** self finished ***")
        self.updateJson()
        self.bouq += 1
        self.loopPlaylists()

    def updateJson(self):
        # print("*** updatejson **")
        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:
                    self.playlists_all[x]["playlist_info"]["bouquet"] = True
                    break
                x += 1

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)

    def done(self, answer=None):
        # print("*** self done **")
        bmx.refreshBouquets()
        self.close()
