#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import globalfunctions as bmx
from . import bouquet_globals as glob
from . import parsem3u as parsem3u
from .plugin import skin_directory, playlists_json, cfg, epgimporter, pythonVer, screenwidth
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

try:
    from urllib import quote
except:
    from urllib.parse import quote

try:
    from xml.dom import minidom
except:
    pass

import os
import json


class BMX_Update(Screen):

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

        self.setup_title = (_("Building Bouquets"))

        self["action"] = Label(_("Building Bouquets..."))
        self["status"] = Label("")
        self["progress"] = ProgressBar()

        self.x = 0

        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            self.bouquets = [item for item in self.playlists_all if item["playlist_info"]["bouquet"] is True]
            self.bouquetslen = len(self.bouquets)

        self.looptimer = eTimer()
        try:
            self.looptimer_conn = self.looptimer.timeout.connect(self.bouquet_loop)
        except:
            self.looptimer.callback.append(self.bouquet_loop)
        self.looptimer.start(100, True)

    def nextjob(self, actiontext, function):
        self["action"].setText(actiontext)
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(function)
        except:
            self.timer.callback.append(function)
        self.timer.start(50, True)

    def loopPlaylists(self):
        if self.x < self.bouquetslen:
            self.bouquet_loop()
        else:
            if self.runtype == "manual":
                self.session.openWithCallback(self.done, MessageBox, str(len(self.bouquets)) + _(" Providers IPTV Updated"), MessageBox.TYPE_INFO, timeout=5)
            else:
                self.done()

    def bouquet_loop(self):
        # print("*** bouquet_loop ***")

        glob.current_playlist = self.bouquets[self.x]

        self.categories = []

        self.livecategoriesdownloaded = False
        self.vodcategoriesdownloaded = False
        self.seriescategoriesdownloaded = False

        self.bouquettv = False
        self.userbouquet = False

        self.totalcount = 0

        self.unique_ref = 0

        self.progressvalue = 0
        self.progressrange = 0

        self.safeName = bmx.safeName(glob.current_playlist["playlist_info"]["name"])

        if glob.current_playlist["settings"]["showlive"] is True and glob.current_playlist["data"]["live_categories"]:
            self.progressrange += 1

        if glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"]:
            self.progressrange += 1

        if glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"]:
            self.progressrange += 1

        self["progress"].setRange((0, self.progressrange))
        self["progress"].setValue(self.progressvalue)
        self["status"].setText(_("Updating Playlist %d of %d") % (self.x + 1, self.bouquetslen))
        self.start()

    def start(self):
        # print("*** start ***")
        self.nextjob(_("Loading playlist...") + str(self.safeName), self.delete_existing_refs)

    def delete_existing_refs(self):
        # print("*** delete_existing_refs ***")

        with open("/etc/enigma2/bouquets.tv", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            f.truncate()

            for line in lines:
                if "bouquetmakerxtream_live_" + str(self.safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(self.safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(self.safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(self.safeName) + ".tv" in line:
                    continue
                f.write(line)

        bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(self.safeName) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(self.safeName) + "_")
        bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(self.safeName) + "_")
        bmx.purge("/etc/enigma2", str(self.safeName) + str(".tv"))

        if epgimporter is True:
            bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(self.safeName))

        self.makeUrlList()

    def makeUrlList(self):
        # print("*** makeUrlList ***")
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        self.full_url = glob.current_playlist["playlist_info"]["full_url"]

        if glob.current_playlist["playlist_info"]["playlisttype"] != "local":

            self.protocol = glob.current_playlist["playlist_info"]["protocol"]
            self.domain = glob.current_playlist["playlist_info"]["domain"]
            self.port = glob.current_playlist["playlist_info"]["port"]

            if self.port:
                self.host = self.protocol + self.domain + ":" + str(self.port)
            else:
                self.host = self.protocol + self.domain

            self.host_encoded = quote(self.host)

            for j in str(self.full_url).lower():
                value = ord(j)
                self.unique_ref += value

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.player_api = str(glob.current_playlist["playlist_info"]["player_api"])
                self.xmltv_api = str(glob.current_playlist["playlist_info"]["xmltv_api"])

                self.username = glob.current_playlist["playlist_info"]["username"]
                self.password = glob.current_playlist["playlist_info"]["password"]
                self.output = glob.current_playlist["playlist_info"]["output"]

                if glob.current_playlist["settings"]["showlive"] is True and glob.current_playlist["data"]["live_categories"]:
                    self.p_live_categories_url = str(self.player_api) + "&action=get_live_categories"
                    self.live_url_list.append([self.p_live_categories_url, 0, "json"])
                    self.p_live_streams_url = self.player_api + "&action=get_live_streams"
                    self.live_url_list.append([self.p_live_streams_url, 3, "json"])

                if glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"]:
                    self.p_vod_categories_url = str(self.player_api) + "&action=get_vod_categories"
                    self.vod_url_list.append([self.p_vod_categories_url, 1, "json"])
                    self.p_vod_streams_url = self.player_api + "&action=get_vod_streams"
                    self.vod_url_list.append([self.p_vod_streams_url, 4, "json"])

                if glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"]:
                    self.p_series_categories_url = str(self.player_api) + "&action=get_series_categories"
                    self.series_url_list.append([self.p_series_categories_url, 2, "json"])
                    self.p_series_streams_url = self.player_api + "&action=get_series"
                    self.series_url_list.append([self.p_series_streams_url, 5, "json"])
                    self.simple = str(self.host) + "/" + "get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=simple&output=" + str(self.output)

            elif glob.current_playlist["playlist_info"]["playlisttype"] == "external":
                self.external_url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6, "text"])
                self.process_downloads("external")
        else:
            self.parse_m3u8_playlist()
            self.nextjob(_("Processing live data..."), self.loadLive)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            if glob.current_playlist["settings"]["showlive"] is True and glob.current_playlist["data"]["live_categories"]:
                self.loadLive()
            elif glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"]:
                self.loadVod()
            elif glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"]:
                self.loadSeries()

    def process_downloads(self, streamtype):
        # print("*** process_downloads ***")

        if streamtype == "live":
            self.url_list = self.live_url_list

        if streamtype == "vod":
            self.url_list = self.vod_url_list

        if streamtype == "series":
            self.url_list = self.series_url_list

        if streamtype == "external":
            self.url_list = self.external_url_list

        for url in self.url_list:
            result = bmx.download_url_multi(url)
            category = result[0]
            response = result[1]

            if response:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if category == 0:
                        glob.current_playlist["data"]["live_categories"] = response
                        # self.nextjob(_("Processing live data..."), self.loadLive)
                        self.livecategoriesdownloaded = True
                    elif category == 1:
                        glob.current_playlist["data"]["vod_categories"] = response
                        # self.nextjob(_("Processing VOD data..."), self.loadVod)
                        self.vodcategoriesdownloaded = True
                    elif category == 2:
                        glob.current_playlist["data"]["series_categories"] = response
                        self.seriescategoriesdownloaded = True
                        # self.nextjob(_("Processing series data..."), self.loadSeries)
                    if category == 3:
                        glob.current_playlist["data"]["live_streams"] = response
                        self.nextjob(_("Processing live data..."), self.loadLive)

                    elif category == 4:
                        glob.current_playlist["data"]["vod_streams"] = response
                        self.nextjob(_("Processing VOD data..."), self.loadVod)

                    elif category == 5:
                        glob.current_playlist["data"]["series_streams"] = response
                        self.nextjob(_("Processing series data..."), self.loadSeries)
                else:
                    self.parse_m3u8_playlist(response)
                    self.livecategoriesdownloaded = True
                    self.vodcategoriesdownloaded = True
                    self.seriescategoriesdownloaded = True
                    self.nextjob(_("Processing m3u8 data..."), self.loadLive)

    def loadLive(self):
        # print("*** loadlive ***")
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("live")

        self.livestreamdata = []
        streamlist = []
        streamtype = glob.current_playlist["settings"]["livetype"]

        self.livecategories = glob.current_playlist["data"]["live_categories"]

        if self.livecategories:
            self.livestreams = glob.current_playlist["data"]["live_streams"]

            if (glob.current_playlist["settings"]["livecategoryorder"] == "alphabetical"):
                self.livecategories = sorted(self.livecategories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["live_categories"]) == len(glob.current_playlist["data"]["live_categories_hidden"]):
                if glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"]:
                    self.loadVod()
                    return
                elif glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"]:
                    self.loadSeries()
                    return
                else:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["settings"]["showlive"] and epgimporter and self.livecategories:
                        self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
                    else:
                        self.finished()

        if self.livecategories and self.livestreams:
            for channel in self.livestreams:
                stream_id = str(channel["stream_id"])

                if str(channel["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["live_streams_hidden"]:

                    name = channel["name"]
                    name = name.replace(":", "").replace('"', "").strip("-")

                    if "tv_archive" in channel:
                        catchup = int(channel["tv_archive"])
                    else:
                        catchup = 0

                    if cfg.catchup.value is True and catchup == 1:
                        name = str(cfg.catchupprefix.value) + str(name)

                    channelid = str(channel["epg_channel_id"])
                    if channelid and "&" in channelid:
                        channelid = channelid.replace("&", "&amp;")

                    bouquet_id1 = 0
                    calc_remainder = int(stream_id) // 65535
                    bouquet_id1 = bouquet_id1 + calc_remainder
                    bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                    serviceref = "1:0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:" + "http%3a//example.m3u8"
                    custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                    if "custom_sid" in channel:
                        if channel["custom_sid"] and channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None and channel["custom_sid"] != "0":

                            if channel["custom_sid"][0].isdigit():
                                channel["custom_sid"] = channel["custom_sid"][1:]

                            serviceref = str(":".join(channel["custom_sid"].split(":")[:7])) + ":0:0:0:" + "http%3a//example.m3u8"
                            custom_sid = channel["custom_sid"]

                    xml_str = ""
                    if channelid and channelid != "None":
                        xml_str = '\t<channel id="' + str(channelid) + '">' + str(serviceref) + '</channel><!-- ' + str(name) + ' -->\n'

                    bouquetString = ""

                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + str(self.host_encoded) + "/live/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(self.output) + ":" + str(name) + "\n"
                    else:
                        source = str(channel["source"])
                        source = quote(source)
                        bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                    bouquetString += "#DESCRIPTION " + str(name) + "\n"

                    streamlist.append({"category_id": str(channel["category_id"]), "xml_str": str(xml_str), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})

        self.livestreamdata = streamlist

        if self.livestreamdata:
            if cfg.groups.value is True and self.bouquettv is False:
                self.build_bouquet_tv_grouped_file()

            bouquetTvString = ""

            if cfg.groups.value is True and self.userbouquet is False:
                bouquetTvString += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            for category in self.livecategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"]:
                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safeName) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    if cfg.groups.value is False:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquetTvString += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_live_" + self.safeName + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            with open(filename, "a+") as f:
                f.write(str(bouquetTvString))

            for category in self.livecategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"]:
                    bouquetTitle = self.safeName + "_" + bmx.safeName(category["category_name"])
                    self.totalcount += 1
                    outputString = ""
                    stringlist = []

                    if glob.current_playlist["settings"]["prefixname"] is True and cfg.groups.value is False:
                        outputString += "#NAME " + self.safeName + " " + category["category_name"] + "\n"
                    else:
                        outputString += "#NAME " + category["category_name"] + "\n"

                    for stream in self.livestreamdata:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])

                    if (glob.current_playlist["settings"]["livestreamorder"] == "alphabetical"):
                        stringlist.sort(key=lambda x: x[1].lower())

                    if (glob.current_playlist["settings"]["livestreamorder"] == "added"):
                        stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in stringlist:
                        outputString += string[0]

                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_live_" + str(bouquetTitle) + ".tv"
                    else:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_live_" + str(bouquetTitle) + ".tv"

                    with open(filename, "w+") as f:
                        f.write(outputString)

        if self.livecategories:
            self.progressvalue += 1
            self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["settings"]["showvod"] and glob.current_playlist["data"]["vod_categories"]:
            self.nextjob(_("Processing VOD data..."), self.loadVod)

        elif glob.current_playlist["settings"]["showseries"] and glob.current_playlist["data"]["series_categories"]:
            self.nextjob(_("Processing series data..."), self.loadSeries)

        else:
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and epgimporter and self.livecategories:
                self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
            else:
                self.finished()

    def loadVod(self):
        # print("*** loadvod ***")
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("vod")

        self.vodstreamdata = []
        streamlist = []
        streamtype = glob.current_playlist["settings"]["vodtype"]

        self.vodcategories = glob.current_playlist["data"]["vod_categories"]

        if self.vodcategories:

            self.vodstreams = glob.current_playlist["data"]["vod_streams"]

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.vodcategories = sorted(self.vodcategories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["vod_categories"]) == len(glob.current_playlist["data"]["vod_categories_hidden"]):
                if glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"]:
                    self.loadSeries()
                    return
                else:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["settings"]["showlive"] and epgimporter and self.livecategories:
                        self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
                    else:
                        self.finished()

        if self.vodcategories and self.vodstreams:
            for channel in self.vodstreams:
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

                    bouquetString = ""

                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + str(self.host_encoded) + "/movie/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(extension) + ":" + str(name) + "\n"
                    else:
                        source = str(channel["source"])
                        source = quote(source)
                        bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                    bouquetString += "#DESCRIPTION " + str(name) + "\n"

                    streamlist.append({"category_id": str(channel["category_id"]), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})

        self.vodstreamdata = streamlist

        if self.vodstreamdata:
            if cfg.groups.value is True and self.bouquettv is False:
                self.build_bouquet_tv_grouped_file()

            bouquetTvString = ""
            if cfg.groups.value is True and self.userbouquet is False:
                bouquetTvString += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

            for category in self.vodcategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"]:
                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safeName) + ".tv"
                        bouquet = "subbouquet"
                        self.userbouquet = True
                    if cfg.groups.value is False:
                        filename = "/etc/enigma2/bouquets.tv"
                        bouquet = "userbouquet"

                    bouquetTvString += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_vod_" + self.safeName + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

            with open(filename, "a+") as f:
                f.write(str(bouquetTvString))

            for category in self.vodcategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"]:
                    bouquetTitle = self.safeName + "_" + bmx.safeName(category["category_name"])
                    self.totalcount += 1
                    outputString = ""
                    stringlist = []

                    if glob.current_playlist["settings"]["prefixname"] is True and cfg.groups.value is False:
                        outputString += "#NAME " + self.safeName + "-VOD " + category["category_name"] + "\n"
                    else:
                        outputString += "#NAME " + "VOD " + category["category_name"] + "\n"

                    for stream in self.vodstreamdata:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                        stringlist.sort(key=lambda x: x[1].lower())

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                        stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in stringlist:
                        outputString += string[0]

                    if cfg.groups.value is True:
                        filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_vod_" + str(bouquetTitle) + ".tv"
                    else:
                        filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_vod_" + str(bouquetTitle) + ".tv"

                    with open(filename, "w+") as f:
                        f.write(outputString)

        if self.vodcategories:
            self.progressvalue += 1
            self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["settings"]["showseries"] and glob.current_playlist["data"]["series_categories"]:
            self.nextjob(_("Processing series data..."), self.loadSeries)

        else:
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["settings"]["showlive"] and epgimporter and self.livecategories:
                self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
            else:
                self.finished()

    def loadSeries(self):
        # print("*** loadseries ***")
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("series")

        self.seriesstreamdata = []
        streamlist = []
        streamtype = glob.current_playlist["settings"]["vodtype"]
        seriessimpleresult = []

        self.seriescategories = glob.current_playlist["data"]["series_categories"]

        if self.seriescategories:

            self.seriesstreams = glob.current_playlist["data"]["series_streams"]

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.seriescategories = sorted(self.seriescategories, key=lambda k: k["category_name"].lower())

            if len(glob.current_playlist["data"]["series_categories"]) == len(glob.current_playlist["data"]["series_categories_hidden"]):
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["settings"]["showlive"] and epgimporter and self.livecategories:
                    self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
                else:
                    self.finished()
                    return

        if self.seriescategories and self.seriesstreams:
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                url = str(self.simple)
                seriessimpleresult = bmx.download_url(url, "text")

                if seriessimpleresult:
                    if "#EXTM3U" in str(seriessimpleresult):
                        self.session.open(MessageBox, _("Your provider does not have the 'simple' API call\nUnable to build series.\nAlternative method might be added in the future."), MessageBox.TYPE_INFO, timeout=10)
                        return streamlist

                    lines = seriessimpleresult.splitlines()

                    if pythonVer == 3:
                        lines = [x for x in lines if "/series/" in x.decode() or "/S01/" in x.decode() or "/E01" in x.decode() and "/live" not in x.decode() and "/movie/" not in x.decode()]
                    else:
                        lines = [x for x in lines if "/series/" in x or "/S01/" in x or "/E01" in x and "/live" not in x and "/movie/" not in x]

                    buildlist = [x for x in self.seriesstreams if str(x["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"] and
                                 str(x["series_id"]) not in glob.current_playlist["data"]["series_streams_hidden"]]

                    if buildlist:
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

                                for channel in buildlist:
                                    if channel['name'] in series_name:
                                        name = channel["name"]
                                        name = name.replace(":", "").replace('"', "").strip("-")
                                        break

                                if name:
                                    bouquet_id1 = 0
                                    calc_remainder = int(series_stream_id) // 65535
                                    bouquet_id1 = bouquet_id1 + calc_remainder
                                    bouquet_id2 = int(series_stream_id) - int(calc_remainder * 65535)

                                    custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"
                                    bouquetString = ""
                                    bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + quote(series_url) + ":" + str(series_name) + "\n"
                                    bouquetString += "#DESCRIPTION " + str(series_name) + "\n"
                                    streamlist.append({"category_id": str(channel["category_id"]), "stream_id": str(series_stream_id), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["last_modified"])})
                                    x += 1
                            streamlist.append({"category_id": str(channel["category_id"]), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})
                        except Exception as e:
                            print(e)

            else:
                for channel in self.seriesstreams:
                    stream_id = str(channel["series_id"])

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"] and str(channel["series_id"]) not in glob.current_playlist["data"]["series_streams_hidden"]:
                        # extension = channel["container_extension"]

                        name = channel["name"]
                        name = name.replace(":", "").replace('"', "").strip("-")

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                        bouquetString = ""

                        source = str(channel["source"])
                        source = quote(source)
                        bouquetString += "#SERVICE " + str(streamtype) + str(custom_sid) + str(source) + ":" + str(name) + "\n"

                        bouquetString += "#DESCRIPTION " + str(name) + "\n"

                        streamlist.append({"category_id": str(channel["category_id"]), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})

            self.seriesstreamdata = streamlist

            if self.seriesstreamdata:

                if cfg.groups.value is True and self.bouquettv is False:
                    self.build_bouquet_tv_grouped_file()

                bouquetTvString = ""

                if cfg.groups.value is True and self.userbouquet is False:
                    bouquetTvString += "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"

                for category in self.seriescategories:

                    if str(category["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"]:
                        bouquetTitle = self.safeName + "_" + bmx.safeName(category["category_name"])
                        if cfg.groups.value is True:
                            filename = "/etc/enigma2/" + "userbouquet.bouquetmakerxtream_" + str(self.safeName) + ".tv"
                            bouquet = "subbouquet"
                            self.userbouquet = True
                        if cfg.groups.value is False:
                            filename = "/etc/enigma2/bouquets.tv"
                            bouquet = "userbouquet"

                        bouquetTvString += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + bouquet + ".bouquetmakerxtream_series_" + self.safeName + "_" + bmx.safeName(category["category_name"]) + '.tv" ORDER BY bouquet\n'

                with open(filename, "a+") as f:

                    f.write(bouquetTvString)

                for category in self.seriescategories:
                    if str(category["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"]:
                        bouquetTitle = self.safeName + "_" + bmx.safeName(category["category_name"])
                        self.totalcount += 1
                        outputString = ""
                        stringlist = []

                        if glob.current_playlist["settings"]["prefixname"] is True and cfg.groups.value is False:
                            outputString += "#NAME " + self.safeName + "-Series " + category["category_name"] + "\n"
                        else:
                            outputString += "#NAME " + "Series " + category["category_name"] + "\n"

                        for stream in self.seriesstreamdata:
                            if str(category["category_id"]) == str(stream["category_id"]):
                                stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])

                        if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                            stringlist.sort(key=lambda x: x[1].lower())

                        if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                            stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                        for string in stringlist:
                            outputString += string[0]

                        if cfg.groups.value is True:
                            filename = "/etc/enigma2/subbouquet.bouquetmakerxtream_series_" + str(bouquetTitle) + ".tv"
                        else:
                            filename = "/etc/enigma2/userbouquet.bouquetmakerxtream_series_" + str(bouquetTitle) + ".tv"

                        with open(filename, "w+") as f:
                            f.write(outputString)
        if self.seriescategories:
            self.progressvalue += 1
            self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["settings"]["showlive"] and epgimporter and self.livecategories:
            self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)
        else:
            self.finished()

    def parse_m3u8_playlist(self, response=None):
        # print("*** parse_m3u8_playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parse_m3u8_playlist(response)
        self.make_m3u8_categories_json()

    def make_m3u8_categories_json(self):
        # print("*** make_m3u8_categories_json  ***")
        parsem3u.make_m3u8_categories_json(self.live_streams, self.vod_streams, self.series_streams)
        self.make_m3u8_streams_json()

    def make_m3u8_streams_json(self):
        # print("*** make_m3u8_streams_json ***")
        parsem3u.make_m3u8_streams_json(self.live_streams, self.vod_streams, self.series_streams)

    def build_bouquet_tv_grouped_file(self):
        # print("*** build_bouquet_tv_grouped_file ***")
        exists = False
        groupname = "userbouquet.bouquetmakerxtream_" + str(self.safeName) + ".tv"
        with open("/etc/enigma2/bouquets.tv", "r") as f:
            for ln, line in enumerate(f):
                if str(groupname) in line:
                    exists = True
                    break

        if exists is False:
            with open("/etc/enigma2/bouquets.tv", "a+") as f:
                bouquetTvString = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(groupname) + '" ORDER BY bouquet\n'
                f.write(str(bouquetTvString))

        self.bouquettv = True

    def build_xmltv_source(self):
        # print("*** build_xmltv_source ***")

        import xml.etree.ElementTree as ET

        filepath = "/etc/epgimport/"
        epgfilename = "bouquetmakerxtream." + str(self.safeName) + ".channels.xml"
        channelpath = os.path.join(filepath, epgfilename)
        sourcefile = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if not os.path.isfile(sourcefile) or os.stat(sourcefile).st_size == 0:
            with open(sourcefile, "w") as f:
                xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
                xml_str += '<sources>\n'
                xml_str += '<sourcecat sourcecatname="BouquetMakerXtream EPG">\n'
                xml_str += '</sourcecat>\n'
                xml_str += '</sources>\n'
                f.write(xml_str)

        tree = ET.parse(sourcefile)
        root = tree.getroot()
        sourcecat = root.find("sourcecat")

        exists = False

        for sourceitem in sourcecat:
            if channelpath in sourceitem.attrib["channels"]:
                exists = True
                break

        if exists is False:
            source = ET.SubElement(sourcecat, "source", type="gen_xmltv", nocheck="1", channels=channelpath)
            description = ET.SubElement(source, "description")
            description.text = str(self.safeName)

            url = ET.SubElement(source, "url")
            url.text = str(self.xmltv_api)

            tree.write(sourcefile)

        try:
            with open(sourcefile, "r+") as f:
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

        self.nextjob(_("Building EPG channel file..."), self.build_xmltv_channels)

    def build_xmltv_channels(self):
        # print("*** build_xmltv channels ***")

        filepath = "/etc/epgimport/"
        epgfilename = "bouquetmakerxtream." + str(self.safeName) + ".channels.xml"
        channelpath = os.path.join(filepath, epgfilename)

        if not os.path.isfile(channelpath):
            open(channelpath, "a").close()

        with open(channelpath, "w") as f:
            xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
            xml_str += '<channels>\n'

            if self.livestreamdata:
                for stream in self.livestreamdata:
                    if stream["xml_str"] and stream["xml_str"] is not None:
                        xml_str += stream["xml_str"]
            xml_str += '</channels>\n'
            f.write(xml_str)
        self.finished()

    def finished(self):
        # print("**** self finished ***")
        self.updateJson()
        self.x += 1
        self.loopPlaylists()

    def updateJson(self):
        # print("*** updatejson ***")
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
        bmx.refreshBouquets()
        self.close()