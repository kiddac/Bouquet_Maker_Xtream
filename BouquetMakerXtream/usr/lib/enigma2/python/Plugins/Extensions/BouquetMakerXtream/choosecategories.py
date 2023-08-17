#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmxfunctions
from .plugin import skin_directory, hdr, common_path, playlists_json, hasConcurrent, hasMultiprocessing, cfg, pythonVer
from .bouquetStaticText import StaticText
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from requests.adapters import HTTPAdapter, Retry
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import os
import json
import re
import requests
try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0
requests.packages.urllib3.disable_warnings()


class BouquetMakerXtream_ChooseCategories(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "categories.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = ""

        self.categoryList = []
        self.channelList = []

        self["list1"] = List(self.categoryList, enableWrapAround=True)
        self["list2"] = List(self.channelList, enableWrapAround=True)

        self.selectedList = self["list1"]
        self.currentList = 1

        self["CategoryTitle"] = StaticText(_("Category"))
        self["ChannelTitle"] = StaticText(_("Channel"))

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText("")
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Reset"))

        self["key_info"] = StaticText(_("Show Streams"))

        self["splash"] = Pixmap()
        self["splash"].show()

        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
            "ok": self.toggleSelection,
            "red": self.keyCancel,
            "cancel": self.keyCancel,
            "green": self.keyGreen,
            "yellow": self.toggleAllSelection,
            "blue": self.clearAllSelection,
            "left": self.goLeft,
            "right": self.goRight,
            "channelUp": self.pageUp,
            "channelDown": self.pageDown,
            "prevBouquet": self.pageUp,
            "nextBouquet": self.pageDown,

            "up": self.goUp,
            "down": self.goDown,

        }, -2)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.player_api = glob.current_playlist["playlist_info"]["player_api"]

            self.p_live_categories_url = str(self.player_api) + "&action=get_live_categories"
            self.p_vod_categories_url = str(self.player_api) + "&action=get_vod_categories"
            self.p_series_categories_url = str(self.player_api) + "&action=get_series_categories"

            self.p_live_streams_url = self.player_api + "&action=get_live_streams"
            self.p_vod_streams_url = self.player_api + "&action=get_vod_streams"
            self.p_series_streams_url = self.player_api + "&action=get_series"

        self.onFirstExecBegin.append(self.start)

    def enablelist(self):
        # print("*** enablelist ***")
        self["list2"].master.master.instance.setSelectionEnable(0)
        self.active = "list" + str(self.currentList)

        if self[self.active].getCurrent():
            self[self.active].master.master.instance.setSelectionEnable(1)
            self.selectedList = self[self.active]
            if self.selectedList == self["list2"]:
                self.selectedList.setIndex(0)
            return True
        else:
            return False

    def goLeft(self):
        success = False
        if self.selectedList.getCurrent():
            while success is False:
                self.currentList -= 1
                if self.currentList < 1:
                    self.currentList = 2
                success = self.enablelist()

    def goRight(self):
        success = False
        if self.selectedList.getCurrent():
            while success is False:
                self.currentList += 1
                if self.currentList > 2:
                    self.currentList = 1
                success = self.enablelist()

    def pageUp(self):
        if self.selectedList.getCurrent():
            instance = self.selectedList.master.master.instance
            instance.moveSelection(instance.pageUp)

            if self.selectedList == self["list1"]:
                self.selectionChanged()

    def pageDown(self):
        if self.selectedList.getCurrent():
            instance = self.selectedList.master.master.instance
            instance.moveSelection(instance.pageDown)

            if self.selectedList == self["list1"]:
                self.selectionChanged()

    def goUp(self):
        if self.selectedList.getCurrent():
            instance = self.selectedList.master.master.instance
            instance.moveSelection(instance.moveUp)

            if self.selectedList == self["list1"]:
                self.selectionChanged()

    def goDown(self):
        if self.selectedList.getCurrent():
            instance = self.selectedList.master.master.instance
            instance.moveSelection(instance.moveDown)

            if self.selectedList == self["list1"]:
                self.selectionChanged()

    def start(self):
        # print("*** start ***")
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(5, True)

    def makeUrlList(self):
        # print("*** makeUrlList ***")
        self.url_list = []
        if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                if glob.current_playlist["settings"]["showlive"] is True:
                    self.url_list.append([self.p_live_categories_url, 0])
                    self.url_list.append([self.p_live_streams_url, 3])

                if glob.current_playlist["settings"]["showvod"] is True:
                    self.url_list.append([self.p_vod_categories_url, 1])
                    self.url_list.append([self.p_vod_streams_url, 4])

                if glob.current_playlist["settings"]["showseries"] is True:
                    self.url_list.append([self.p_series_categories_url, 2])
                    self.url_list.append([self.p_series_streams_url, 5])

            elif glob.current_playlist["playlist_info"]["playlisttype"] == "external":
                self.url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6])
            self.process_downloads()
        else:
            self.parse_m3u8_playlist()

        self["splash"].hide()
        if glob.current_playlist["settings"]["showlive"] is True and glob.current_playlist["data"]["live_categories"] != []:
            self.loadLive()
        elif glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"] != []:
            self.loadVod()
        elif glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"] != []:
            self.loadSeries()

    def download_url(self, url):
        # print("*** download_url ***")
        category = url[1]
        r = ""

        retries = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""

        # print("*** url ***", url)
        try:
            r = http.get(url[0], headers=hdr, timeout=(10, 20), verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                if category != 6:
                    try:
                        response = r.json()
                        return category, response
                    except Exception as e:
                        print(e)
                        return category, ""
                else:
                    try:
                        response = r.text
                        return category, response
                    except Exception as e:
                        print(e)
                        return category, ""

        except Exception as e:
            print(e)
            return category, ""

    def process_downloads(self):
        # print("*** process_downloads ***")

        threads = len(self.url_list)
        if threads > 10:
            threads = 10

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    # print("******* trying concurrent futures ******")
                    from concurrent.futures import ThreadPoolExecutor
                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(self.download_url, self.url_list)
                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    # print("*** trying multiprocessing ThreadPool ***")
                    from multiprocessing.pool import ThreadPool
                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(self.download_url, self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print(e)

            for category, response in results:
                if response:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        if category == 0:
                            glob.current_playlist["data"]["live_categories"] = response
                        elif category == 1:
                            glob.current_playlist["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.current_playlist["data"]["series_categories"] = response
                        elif category == 3:
                            glob.current_playlist["data"]["live_streams"] = response
                        elif category == 4:
                            glob.current_playlist["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.current_playlist["data"]["series_streams"] = response
                    else:
                        self.parse_m3u8_playlist(response)

        else:
            # print("*** trying sequential ***")
            for url in self.url_list:
                result = self.download_url(url)
                category = result[0]
                response = result[1]
                if response:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        # add categories to main json file
                        if category == 0:
                            glob.current_playlist["data"]["live_categories"] = response
                        elif category == 1:
                            glob.current_playlist["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.current_playlist["data"]["series_categories"] = response
                        elif category == 3:
                            glob.current_playlist["data"]["live_streams"] = response
                        elif category == 4:
                            glob.current_playlist["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.current_playlist["data"]["series_streams"] = response
                    else:
                        self.parse_m3u8_playlist(response)

    def parse_m3u8_playlist(self, response=None):
        # print("*** parse_m3u8_playlist ***")
        self.live_streams = []
        self.vod_streams = []
        self.series_streams = []
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
                    group_title = re.search('group-title=\"(.*?)\"', line).group(1).strip()

                if "tvg-name=" in line:
                    name = re.search('tvg-name=\"(.*?)\"', line).group(1).strip()

                else:
                    name = line.strip().split(",")[1]

                if name == "":
                    channelnum += 1
                    name = _("Stream") + " " + str(channelnum)

                if "tvg-id=" in line:
                    epg_id = re.search('tvg-id=\"(.*?)\"', line).group(1).strip()

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
                    self.live_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif streamtype == "vod" and glob.current_playlist["settings"]["showvod"] is True:
                    if group_title == "":
                        group_title = "Uncategorised VOD"

                    streamid += 1
                    self.vod_streams.append([epg_id, logo, group_title, name, source, streamid])

                elif streamtype == "series" and glob.current_playlist["settings"]["showseries"] is True:
                    if group_title == "":
                        group_title = "Uncategorised Series"
                    streamid += 1
                    self.series_streams.append([epg_id, logo, group_title, name, source, streamid])

                else:
                    if group_title == "":
                        group_title = "Uncategorised"
                    streamid += 1
                    self.live_streams.append([epg_id, logo, group_title, name, source, streamid])

        self.make_m3u8_categories_json()

    def make_m3u8_categories_json(self):
        # print("*** make_m3u8_categories_json ***")
        glob.current_playlist["data"]["live_categories"] = []
        glob.current_playlist["data"]["vod_categories"] = []
        glob.current_playlist["data"]["series_categories"] = []

        for x in self.live_streams:
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

        for x in self.vod_streams:
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

        for x in self.series_streams:
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

        # print(glob.current_playlist["data"])

        self.make_m3u8_streams_json()

    def make_m3u8_streams_json(self):
        # print("*** make_m3u8_streams_json ***")
        glob.current_playlist["data"]["live_streams"] = []
        glob.current_playlist["data"]["vod_streams"] = []
        glob.current_playlist["data"]["series_streams"] = []

        for x in self.live_streams:
            glob.current_playlist["data"]["live_streams"].append({"epg_channel_id": str(x[0]), "stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "stream_id": str(x[5])})

        for x in self.vod_streams:
            glob.current_playlist["data"]["vod_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "stream_id": str(x[5])})

        for x in self.series_streams:
            glob.current_playlist["data"]["series_streams"].append({"stream_icon": str(x[1]), "category_id": str(x[2]), "name":  str(x[3]), "source": str(x[4]), "series_id": str(x[5])})

    def loadLive(self):
        # print("*** loadlive ***")
        self.categoryList = []
        self.categorySelectedList = []

        self.setup_title = _("Choose Live Categories")
        self.setTitle(self.setup_title)

        if (glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"] != []) or (glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"] != []):
            self["key_green"].setText(_("Next"))
        else:
            self["key_green"].setText(_("Create"))

        for category in glob.current_playlist["data"]["live_categories"]:
            if str(category["category_id"]) in glob.current_playlist["data"]["live_categories_hidden"]:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
            else:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

        if (glob.current_playlist["settings"]["liveorder"] == "alphabetical"):
            self.categorySelectedList.sort(key=lambda x: x[1].lower())

        self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]

        self["list1"].setList(self.categoryList)
        self["list1"].setIndex(0)
        self.currentList = 1
        self.enablelist()
        self.selectionChanged()

    def loadVod(self):
        # print("*** loadvod  ***")
        self.categoryList = []
        self.categorySelectedList = []

        self.setup_title = _("Choose VOD Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"] != []:
            self["key_green"].setText(_("Next"))
        else:
            self["key_green"].setText(_("Create"))

        for category in glob.current_playlist["data"]["vod_categories"]:
            if str(category["category_id"]) in glob.current_playlist["data"]["vod_categories_hidden"]:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
            else:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

        if (glob.current_playlist["settings"]["liveorder"] == "alphabetical"):
            self.categorySelectedList.sort(key=lambda x: x[1].lower())

        self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
        self["list1"].setList(self.categoryList)
        self["list1"].setIndex(0)
        self.currentList = 1
        self.enablelist()
        self.selectionChanged()

    def loadSeries(self):
        # print("*** loadseries ***")
        self.categoryList = []
        self.categorySelectedList = []

        self.setup_title = _("Choose Series Categories")
        self.setTitle(self.setup_title)

        self["key_green"].setText(_("Create"))

        for category in glob.current_playlist["data"]["series_categories"]:
            if str(category["category_id"]) in glob.current_playlist["data"]["series_categories_hidden"]:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
            else:
                self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

        self.categorySelectedList.sort(key=lambda x: x[1].lower())

        self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
        self["list1"].setList(self.categoryList)
        self["list1"].setIndex(0)
        self.currentList = 1
        self.enablelist()
        self.selectionChanged()

    def selectionChanged(self):
        if not self["list1"].getCurrent():
            # print("**** no list1 ***")
            return

        if self["list1"].getCurrent()[3] is True:
            self["list2"].setList([])
            return

        category = self["list1"].getCurrent()[2]

        self.channelList = []
        self.channelSelectedList = []

        if self.setup_title == (_("Choose Live Categories")):

            for channel in glob.current_playlist["data"]["live_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False])

        elif self.setup_title == (_("Choose VOD Categories")):
            for channel in glob.current_playlist["data"]["vod_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False])

        elif self.setup_title == (_("Choose Series Categories")):
            for channel in glob.current_playlist["data"]["series_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["series_id"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), True])
                        else:
                            self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), False])
                else:
                    if str(channel["name"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                        self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), True])
                    else:
                        self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), False])

        self.channelSelectedList.sort(key=lambda x: x[1].lower())

        self.channelList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channelSelectedList]
        self["list2"].setList(self.channelList)
        self.currentList = 1
        self.enablelist()

    def buildListEntry(self, id, name, enabled):
        if enabled:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_off.png"))
        return (pixmap, str(name), str(id), enabled)

    def refresh(self):
        # print("*** refresh ***")
        if self.selectedList == self["list1"]:
            self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].updateList(self.categoryList)

            if self.setup_title == (_("Choose Live Categories")):
                glob.current_playlist["data"]["live_categories_hidden"] = []
                for hidden in self.categorySelectedList:
                    if hidden[2] is True:
                        glob.current_playlist["data"]["live_categories_hidden"].append(hidden[0])

            elif self.setup_title == (_("Choose VOD Categories")):
                glob.current_playlist["data"]["vod_categories_hidden"] = []
                for hidden in self.categorySelectedList:
                    if hidden[2] is True:
                        glob.current_playlist["data"]["vod_categories_hidden"].append(hidden[0])

            elif self.setup_title == (_("Choose Series Categories")):
                glob.current_playlist["data"]["series_categories_hidden"] = []
                for hidden in self.categorySelectedList:
                    if hidden[2] is True:
                        glob.current_playlist["data"]["series_categories_hidden"].append(hidden[0])

            if self["list1"].getCurrent()[3] is True:
                self["list2"].setList([])
            else:
                self.channelList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channelSelectedList]
                self["list2"].updateList(self.channelList)

            self.selectionChanged()

        if self.selectedList == self["list2"]:
            self.channelList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channelSelectedList]
            self["list2"].updateList(self.channelList)

            if self.setup_title == (_("Choose Live Categories")):
                glob.current_playlist["data"]["live_streams_hidden"] = []
                for hidden in self.channelSelectedList:
                    if hidden[2] is True:
                        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                            glob.current_playlist["data"]["live_streams_hidden"].append(hidden[0])
                        else:
                            glob.current_playlist["data"]["live_streams_hidden"].append(hidden[1])

            elif self.setup_title == (_("Choose VOD Categories")):
                glob.current_playlist["data"]["vod_streams_hidden"] = []
                for hidden in self.channelSelectedList:
                    if hidden[2] is True:
                        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                            glob.current_playlist["data"]["vod_streams_hidden"].append(hidden[0])
                        else:
                            glob.current_playlist["data"]["vod_streams_hidden"].append(hidden[1])

            elif self.setup_title == (_("Choose Series Categories")):
                glob.current_playlist["data"]["series_streams_hidden"] = []
                for hidden in self.channelSelectedList:
                    if hidden[2] is True:
                        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                            glob.current_playlist["data"]["series_streams_hidden"].append(hidden[0])
                        else:
                            glob.current_playlist["data"]["seires_streams_hidden"].append(hidden[1])

    def toggleSelection(self):
        if len(self[self.active].list) > 0:
            idx = self[self.active].getIndex()

            if self.selectedList == self["list1"]:
                self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

            elif self.selectedList == self["list2"]:
                self.channelSelectedList[idx][2] = not self.channelSelectedList[idx][2]
        self.refresh()

    def toggleAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selectedList == self["list1"]:
                    self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

                elif self.selectedList == self["list2"]:
                    self.channelSelectedList[idx][2] = not self.channelSelectedList[idx][2]
        self.refresh()

    def clearAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selectedList == self["list1"]:
                    self.categorySelectedList[idx][2] = False

                elif self.selectedList == self["list2"]:
                    self.channelSelectedList[idx][2] = False
        self.refresh()

    def keyCancel(self):
        if self.setup_title == (_("Choose Series Categories")):
            if glob.current_playlist["settings"]["showvod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["showlive"] is True:
                self.loadLive()
            else:
                self.close()

        elif self.setup_title == (_("Choose VOD Categories")):
            if glob.current_playlist["settings"]["showlive"] is True:
                self.loadLive()
            else:
                self.close()

        elif self.setup_title == (_("Choose Live Categories")):
            self.close()

    def keyGreen(self):
        # print("*** keygreen ***")
        if self.setup_title == (_("Choose Live Categories")):
            if glob.current_playlist["settings"]["showvod"] is True and glob.current_playlist["data"]["vod_categories"] != []:
                self.loadVod()
            elif glob.current_playlist["settings"]["showseries"] is True and glob.current_playlist["data"]["series_categories"] != []:
                self.loadSeries()
            else:
                self.save()

        elif self.setup_title == (_("Choose VOD Categories")):
            if glob.current_playlist["settings"]["showseries"] is True:
                self.loadSeries()
            else:
                self.save()

        elif self.setup_title == (_("Choose Series Categories")):
            self.save()

    def save(self):
        # print("**** save data ***")
        self.getPlaylistUserFile()
        from . import buildbouquets
        self.session.openWithCallback(self.exit, buildbouquets.BouquetMakerXtream_BuildBouquets)

    def exit(self, answer="none"):
        self.close(True)

    def getPlaylistUserFile(self):
        self.playlists_all = bmxfunctions.getPlaylistJson()

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:

                    glob.current_playlist["data"]["live_streams"] = []
                    glob.current_playlist["data"]["vod_streams"] = []
                    glob.current_playlist["data"]["series_streams"] = []

                    self.playlists_all[x]["data"]["live_categories"] = glob.current_playlist["data"]["live_categories"]
                    self.playlists_all[x]["data"]["vod_categories"] = glob.current_playlist["data"]["vod_categories"]
                    self.playlists_all[x]["data"]["series_categories"] = glob.current_playlist["data"]["series_categories"]

                    self.playlists_all[x]["data"]["live_streams"] = glob.current_playlist["data"]["live_streams"]
                    self.playlists_all[x]["data"]["vod_streams"] = glob.current_playlist["data"]["vod_streams"]
                    self.playlists_all[x]["data"]["series_streams"] = glob.current_playlist["data"]["series_streams"]

                    self.playlists_all[x]["data"]["live_categories_hidden"] = glob.current_playlist["data"]["live_categories_hidden"]
                    self.playlists_all[x]["data"]["vod_categories_hidden"] = glob.current_playlist["data"]["vod_categories_hidden"]
                    self.playlists_all[x]["data"]["series_categories_hidden"] = glob.current_playlist["data"]["series_categories_hidden"]

                    self.playlists_all[x]["data"]["live_streams_hidden"] = glob.current_playlist["data"]["live_streams_hidden"]
                    self.playlists_all[x]["data"]["vod_streams_hidden"] = glob.current_playlist["data"]["vod_streams_hidden"]
                    self.playlists_all[x]["data"]["series_streams_hidden"] = glob.current_playlist["data"]["series_streams_hidden"]

                    break
                x += 1

        self.writeJsonFile()

    def writeJsonFile(self):
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
