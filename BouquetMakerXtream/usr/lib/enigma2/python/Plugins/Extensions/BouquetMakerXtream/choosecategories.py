#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import globalfunctions as bmx
from . import bouquet_globals as glob
from . import parsem3u as parsem3u
from .plugin import skin_directory, common_path, playlists_json, hasConcurrent, hasMultiprocessing, cfg
from .bouquetStaticText import StaticText
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import os
import json


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

        self.level = 1
        self.data = False

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
        print("*** show splash 1 ***")
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
            "2": self.pageUp,
            "8": self.pageDown,
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
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                if glob.current_playlist["settings"]["showlive"] is True:
                    self.live_url_list.append([self.p_live_categories_url, 0, "json"])
                    self.live_url_list.append([self.p_live_streams_url, 3, "json"])

                if glob.current_playlist["settings"]["showvod"] is True:
                    self.vod_url_list.append([self.p_vod_categories_url, 1, "json"])
                    self.vod_url_list.append([self.p_vod_streams_url, 4, "json"])

                if glob.current_playlist["settings"]["showseries"] is True:
                    self.series_url_list.append([self.p_series_categories_url, 2, "json"])
                    self.series_url_list.append([self.p_series_streams_url, 5, "json"])

            elif glob.current_playlist["playlist_info"]["playlisttype"] == "external":
                self.external_url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6, "text"])
                self.process_downloads("external")
        else:
            self.parse_m3u8_playlist()

        try:
            self["splash"].hide()
        except:
            pass

        if glob.current_playlist["settings"]["showlive"] is True:
            self.loadLive()
        elif glob.current_playlist["settings"]["showvod"] is True:
            self.loadVod()
        elif glob.current_playlist["settings"]["showseries"] is True:
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

        try:
            self["splash"].show()
        except:
            pass

        results = ""

        threads = len(self.url_list)
        if threads > 10:
            threads = 10

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(bmx.download_url_multi, self.url_list)
                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    from multiprocessing.pool import ThreadPool
                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(bmx.download_url_multi, self.url_list)
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
            for url in self.url_list:
                result = bmx.download_url_multi(url)
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
        try:
            self["splash"].hide()
        except:
            pass

    def parse_m3u8_playlist(self, response=None):
        # print("*** parse_m3u8_playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parse_m3u8_playlist(response)
        self.make_m3u8_categories_json()

    def make_m3u8_categories_json(self):
        # print("*** make_m3u8_categories_json  ***")
        parsem3u.make_m3u8_categories_json(self.live_streams, self.vod_streams, self.series_streams)
        self.make_m3u8_streams_json()

    def make_m3u8_streams_json(self):
        # print("*** make_m3u8_streams_json  ***")
        parsem3u.make_m3u8_streams_json(self.live_streams, self.vod_streams, self.series_streams)

    def loadLive(self):
        # print("*** loadLive ***")
        self.level = 1
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("live")

        self.setup_title = _("Choose Live Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["data"]["live_categories"]:
            self.categoryList = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["showvod"] is True or glob.current_playlist["settings"]["showseries"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.current_playlist["data"]["live_categories"]:
                categorycount = len(category)

                if str(category["category_id"]) in glob.current_playlist["data"]["live_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True, categorycount, 0])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False, categorycount, 0])

            if (glob.current_playlist["settings"]["livecategoryorder"] == "alphabetical"):
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]

            self["list1"].setList(self.categoryList)
            self["list1"].setIndex(0)
            self.currentList = 1
            self.data = True
            self.enablelist()
            self.selectionChanged()
        else:
            glob.current_playlist["settings"]["showlive"] = False
            if glob.current_playlist["settings"]["showvod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["showseries"] is True:
                self.loadSeries()

    def loadVod(self):
        self.level = 2
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("vod")

        self.setup_title = _("Choose VOD Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["data"]["vod_categories"]:
            self.categoryList = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["showseries"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.current_playlist["data"]["vod_categories"]:
                if str(category["category_id"]) in glob.current_playlist["data"]["vod_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.categoryList)
            self["list1"].setIndex(0)
            self.currentList = 1
            self.data = True
            self.enablelist()
            self.selectionChanged()

        else:
            glob.current_playlist["settings"]["showvod"] = False
            if glob.current_playlist["settings"]["showseries"] is True:
                self.loadSeries()

    def loadSeries(self):
        self.level = 3
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.process_downloads("series")

        self.setup_title = _("Choose Series Categories")
        self.setTitle(self.setup_title)

        self.categoryList = []
        self.categorySelectedList = []

        self["key_green"].setText(_("Create"))

        if glob.current_playlist["data"]["series_categories"]:
            for category in glob.current_playlist["data"]["series_categories"]:
                if str(category["category_id"]) in glob.current_playlist["data"]["series_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.categoryList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.categoryList)
            self["list1"].setIndex(0)
            self.currentList = 1
            self.data = True
            self.enablelist()
            self.selectionChanged()
        else:
            self.save()

    def selectionChanged(self):
        self["list2"].setList([])
        self.channelList = []
        self.channelSelectedList = []

        if not self["list1"].getCurrent():
            return

        if self["list1"].getCurrent()[3] is True:
            self["list2"].setList([])
            return

        category = self["list1"].getCurrent()[2]

        if self.level == 1:

            for channel in glob.current_playlist["data"]["live_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if (glob.current_playlist["settings"]["livestreamorder"] == "alphabetical"):
                self.channelSelectedList.sort(key=lambda x: x[1].lower())

            if (glob.current_playlist["settings"]["livestreamorder"] == "added"):
                self.channelSelectedList.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 2:
            for channel in glob.current_playlist["data"]["vod_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channelSelectedList.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                self.channelSelectedList.sort(key=lambda x: x[1].lower())

            if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                self.channelSelectedList.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 3:
            for channel in glob.current_playlist["data"]["series_streams"]:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["series_id"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                            self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), True, str(channel["last_modified"])])
                        else:
                            self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), False, str(channel["last_modified"])])
                else:
                    if str(channel["name"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                        self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), True, "0"])
                    else:
                        self.channelSelectedList.append([str(channel["series_id"]), str(channel["name"]), False, "0"])

            if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                self.channelSelectedList.sort(key=lambda x: x[1].lower())

            if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                self.channelSelectedList.sort(key=lambda x: x[3].lower(), reverse=True)

        self.channelList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channelSelectedList]
        self["list2"].setList(self.channelList)
        self.currentList = 1
        self.enablelist()

    def buildListEntry(self, id, name, hidden):
        if hidden:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_hidden.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        return (pixmap, str(name), str(id), hidden)

    def refresh(self):
        if self.selectedList == self["list1"]:
            if self["list1"].getCurrent():

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
            if self["list1"].getCurrent():
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
                                glob.current_playlist["data"]["series_streams_hidden"].append(hidden[1])

    def toggleSelection(self):
        if len(self[self.active].list) > 0:
            idx = self[self.active].getIndex()

            if self.selectedList == self["list1"] and self["list1"].getCurrent():
                self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

            elif self.selectedList == self["list2"] and self["list2"].getCurrent():
                self.channelSelectedList[idx][2] = not self.channelSelectedList[idx][2]
        self.refresh()

    def toggleAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selectedList == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

                elif self.selectedList == self["list2"] and self["list2"].getCurrent():
                    self.channelSelectedList[idx][2] = not self.channelSelectedList[idx][2]
        self.refresh()

    def clearAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selectedList == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = False

                elif self.selectedList == self["list2"] and self["list2"].getCurrent():
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
        if self.setup_title == (_("Choose Live Categories")):
            if glob.current_playlist["settings"]["showvod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["showseries"] is True:
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
        self.updateJson()
        from . import buildbouquets
        self.session.openWithCallback(self.exit, buildbouquets.BouquetMakerXtream_BuildBouquets)

    def exit(self, answer="none"):
        self.close(True)

    def updateJson(self, answer="none"):
        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:

                    self.playlists_all[x]["data"]["live_categories"] = glob.current_playlist["data"]["live_categories"]
                    self.playlists_all[x]["data"]["vod_categories"] = glob.current_playlist["data"]["vod_categories"]
                    self.playlists_all[x]["data"]["series_categories"] = glob.current_playlist["data"]["series_categories"]

                    self.playlists_all[x]["data"]["live_streams"] = []
                    self.playlists_all[x]["data"]["vod_streams"] = []
                    self.playlists_all[x]["data"]["series_streams"] = []

                    self.playlists_all[x]["data"]["live_categories_hidden"] = glob.current_playlist["data"]["live_categories_hidden"]
                    self.playlists_all[x]["data"]["vod_categories_hidden"] = glob.current_playlist["data"]["vod_categories_hidden"]
                    self.playlists_all[x]["data"]["series_categories_hidden"] = glob.current_playlist["data"]["series_categories_hidden"]

                    self.playlists_all[x]["data"]["live_streams_hidden"] = glob.current_playlist["data"]["live_streams_hidden"]
                    self.playlists_all[x]["data"]["vod_streams_hidden"] = glob.current_playlist["data"]["vod_streams_hidden"]
                    self.playlists_all[x]["data"]["series_streams_hidden"] = glob.current_playlist["data"]["series_streams_hidden"]

                    break
                x += 1

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
