#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, hasConcurrent, hasMultiprocessing, playlists_json, skin_directory

from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import json
import os


class BmxChooseCategories(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "categories.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = ""

        self.category_list = []
        self.channel_list = []

        self.level = 1

        self["list1"] = List(self.category_list, enableWrapAround=True)
        self["list2"] = List(self.channel_list, enableWrapAround=True)

        self.selected_list = self["list1"]
        self.current_list = 1

        self["CategoryTitle"] = StaticText(_("Category"))
        self["ChannelTitle"] = StaticText(_("Channel"))

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText("")
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Reset"))

        self["key_info"] = StaticText(_("Show Streams"))

        self["splash"] = Pixmap()
        self["splash"].show()

        self.timer = eTimer()

        self["actions"] = ActionMap(["BMXActions"], {
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

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            self.player_api = glob.current_playlist["playlist_info"]["player_api"]
            self.live_streams_api = self.player_api + "&action=get_live_streams"
            self.vod_streams_api = self.player_api + "&action=get_vod_streams"
            self.series_streams_api = self.player_api + "&action=get_series"

        self.onFirstExecBegin.append(self.start)

    def enableList(self):
        self["list2"].master.master.instance.setSelectionEnable(0)
        self.active = "list" + str(self.current_list)

        if self[self.active].getCurrent():
            self[self.active].master.master.instance.setSelectionEnable(1)
            self.selected_list = self[self.active]
            if self.selected_list == self["list2"]:
                self.selected_list.setIndex(0)
            return True
        return False

    def goLeft(self):
        success = False
        if self.selected_list.getCurrent():
            while success is False:
                self.current_list -= 1
                if self.current_list < 1:
                    self.current_list = 2
                success = self.enableList()

    def goRight(self):
        success = False
        if self.selected_list.getCurrent():
            while success is False:
                self.current_list += 1
                if self.current_list > 2:
                    self.current_list = 1
                success = self.enableList()

    def pageUp(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.pageUp)

            if self.selected_list == self["list1"]:
                self.selectionChanged()

    def pageDown(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.pageDown)

            if self.selected_list == self["list1"]:
                self.selectionChanged()

    def goUp(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.moveUp)

            if self.selected_list == self["list1"]:
                self.selectionChanged()

    def goDown(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.moveDown)

            if self.selected_list == self["list1"]:
                self.selectionChanged()

    def start(self):
        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(10, True)

    def makeUrlList(self):
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_live"] is True:
                    self.live_url_list.append([self.live_streams_api, 3, "json"])

                if glob.current_playlist["settings"]["show_vod"] is True:
                    self.vod_url_list.append([self.vod_streams_api, 4, "json"])

                if glob.current_playlist["settings"]["show_series"] is True:
                    self.series_url_list.append([self.series_streams_api, 5, "json"])

        try:
            self["splash"].hide()
        except:
            pass

        if glob.current_playlist["settings"]["show_live"] is True:
            self.loadLive()
        elif glob.current_playlist["settings"]["show_vod"] is True:
            self.loadVod()
        elif glob.current_playlist["settings"]["show_series"] is True:
            self.loadSeries()

    def processDownloads(self, stream_type):
        print("*** processDownloads ***", stream_type)
        stream_map = {
            "live": self.live_url_list,
            "vod": self.vod_url_list,
            "series": self.series_url_list,
            "external": self.external_url_list
        }
        self.url_list = stream_map.get(stream_type, [])

        try:
            self["splash"].show()
        except:
            pass

        results = ""
        threads = min(len(self.url_list), 10)

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    with ThreadPoolExecutor(max_workers=threads) as executor:
                        results = executor.map(bmx.downloadUrlMulti, self.url_list)

                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    from multiprocessing.pool import ThreadPool

                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(bmx.downloadUrlMulti, self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print(e)

            for category, response in results:
                if response:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        if category == 3:
                            glob.current_playlist["data"]["live_streams"] = response
                        elif category == 4:
                            glob.current_playlist["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.current_playlist["data"]["series_streams"] = response

        else:
            for url in self.url_list:
                category, response = bmx.downloadUrlMulti(url)
                if response:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        # add categories to main json file
                        if category == 3:
                            glob.current_playlist["data"]["live_streams"] = response
                        elif category == 4:
                            glob.current_playlist["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.current_playlist["data"]["series_streams"] = response

        keys_to_remove = set(['num', 'cover', 'plot', 'cast', 'director', 'genre', 'rating', 'rating_5based', 'backdrop_path', "youtube_trailer", "tmdb", "episode_run_time", "category_ids"])
        for data in glob.current_playlist["data"].get("series_streams", []):
            try:
                keys_to_remove.intersection_update(data.keys())
                for key in keys_to_remove:
                    del data[key]
            except Exception as e:
                print(e)
        try:
            self["splash"].hide()
        except:
            pass

    def loadLive(self):
        self.level = 1
        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            self.processDownloads("live")

        self.setup_title = _("Choose Live Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["data"]["live_categories"]:
            self.category_list = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["show_vod"] is True or glob.current_playlist["settings"]["show_series"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.current_playlist["data"]["live_categories"]:

                if str(category["category_id"]) in glob.current_playlist["data"]["live_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if glob.current_playlist["settings"]["live_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]

            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.enableList()
            self.selectionChanged()
        else:
            glob.current_playlist["settings"]["show_live"] = False
            if glob.current_playlist["settings"]["show_vod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["show_series"] is True:
                self.loadSeries()

    def loadVod(self):
        self.level = 2
        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            self.processDownloads("vod")

        self.setup_title = _("Choose VOD Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["data"]["vod_categories"]:
            self.category_list = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["show_series"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.current_playlist["data"]["vod_categories"]:
                if str(category["category_id"]) in glob.current_playlist["data"]["vod_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.enableList()
            self.selectionChanged()

        else:
            glob.current_playlist["settings"]["show_vod"] = False
            if glob.current_playlist["settings"]["show_series"] is True:
                self.loadSeries()

    def loadSeries(self):
        self.level = 3
        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            self.processDownloads("series")

        self.setup_title = _("Choose Series Categories")
        self.setTitle(self.setup_title)

        self.category_list = []
        self.categorySelectedList = []

        self["key_green"].setText(_("Create"))

        if glob.current_playlist["data"]["series_categories"]:
            for category in glob.current_playlist["data"]["series_categories"]:
                if str(category["category_id"]) in glob.current_playlist["data"]["series_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if glob.current_playlist["settings"]["vod_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.enableList()
            self.selectionChanged()
        else:
            self.save()

    def selectionChanged(self):
        self["list2"].setList([])
        self.channel_list = []
        self.channel_selected_list = []

        if not self["list1"].getCurrent():
            return

        if self["list1"].getCurrent()[3] is True:
            self["list2"].setList([])
            return

        category = self["list1"].getCurrent()[2]

        if self.level == 1:
            for channel in glob.current_playlist["data"]["live_streams"]:
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if glob.current_playlist["settings"]["live_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["live_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 2:
            for channel in glob.current_playlist["data"]["vod_streams"]:
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 3:
            for channel in glob.current_playlist["data"]["series_streams"]:
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["series_id"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), True, str(channel["last_modified"])])
                        else:
                            self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), False, str(channel["last_modified"])])
                else:
                    if str(channel["name"]) in glob.current_playlist["data"]["series_streams_hidden"]:
                        self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), True, "0"])
                    else:
                        self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), False, "0"])

            if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
        self["list2"].setList(self.channel_list)
        self.current_list = 1
        self.enableList()

    def buildListEntry(self, id, name, hidden):
        if hidden:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_hidden.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        return (pixmap, str(name), str(id), hidden)

    def refresh(self):
        if self.selected_list == self["list1"]:
            if self["list1"].getCurrent():
                self.category_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
                self["list1"].updateList(self.category_list)

                if self.setup_title == (_("Choose Live Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.current_playlist["data"]["live_categories_hidden"]:
                                glob.current_playlist["data"]["live_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.current_playlist["data"]["live_categories_hidden"]:
                                glob.current_playlist["data"]["live_categories_hidden"].remove(hidden[0])

                elif self.setup_title == (_("Choose VOD Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.current_playlist["data"]["vod_categories_hidden"]:
                                glob.current_playlist["data"]["vod_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.current_playlist["data"]["vod_categories_hidden"]:
                                glob.current_playlist["data"]["vod_categories_hidden"].remove(hidden[0])

                elif self.setup_title == (_("Choose Series Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.current_playlist["data"]["series_categories_hidden"]:
                                glob.current_playlist["data"]["series_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.current_playlist["data"]["series_categories_hidden"]:
                                glob.current_playlist["data"]["series_categories_hidden"].remove(hidden[0])

                if self["list1"].getCurrent()[3] is True:
                    self["list2"].setList([])
                else:
                    self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                    self["list2"].updateList(self.channel_list)

                self.selectionChanged()

        if self.selected_list == self["list2"]:
            if self["list1"].getCurrent():
                self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                self["list2"].updateList(self.channel_list)

                if self.setup_title == (_("Choose Live Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.current_playlist["data"]["live_streams_hidden"]:
                                    glob.current_playlist["data"]["live_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.current_playlist["data"]["live_streams_hidden"]:
                                    glob.current_playlist["data"]["live_streams_hidden"].append(hidden[1])
                        else:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.current_playlist["data"]["live_streams_hidden"]:
                                    glob.current_playlist["data"]["live_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.current_playlist["data"]["live_streams_hidden"]:
                                    glob.current_playlist["data"]["live_streams_hidden"].remove(hidden[1])

                elif self.setup_title == (_("Choose VOD Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.current_playlist["data"]["vod_streams_hidden"]:
                                    glob.current_playlist["data"]["vod_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.current_playlist["data"]["vod_streams_hidden"]:
                                    glob.current_playlist["data"]["vod_streams_hidden"].append(hidden[1])
                        else:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.current_playlist["data"]["vod_streams_hidden"]:
                                    glob.current_playlist["data"]["vod_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.current_playlist["data"]["vod_streams_hidden"]:
                                    glob.current_playlist["data"]["vod_streams_hidden"].remove(hidden[1])

                elif self.setup_title == (_("Choose Series Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.current_playlist["data"]["series_streams_hidden"]:
                                    glob.current_playlist["data"]["series_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.current_playlist["data"]["series_streams_hidden"]:
                                    glob.current_playlist["data"]["series_streams_hidden"].append(hidden[1])
                        else:
                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.current_playlist["data"]["series_streams_hidden"]:
                                    glob.current_playlist["data"]["series_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.current_playlist["data"]["series_streams_hidden"]:
                                    glob.current_playlist["data"]["series_streams_hidden"].remove(hidden[1])

    def toggleSelection(self):
        if len(self[self.active].list) > 0:
            idx = self[self.active].getIndex()

            if self.selected_list == self["list1"] and self["list1"].getCurrent():
                self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

            elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def toggleAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def clearAllSelection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = False

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = False
        self.refresh()

    def keyCancel(self):
        if self.setup_title == _("Choose Series Categories"):
            if glob.current_playlist["settings"]["show_vod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["show_live"] is True:
                self.loadLive()
            else:
                self.close()

        elif self.setup_title == _("Choose VOD Categories"):
            if glob.current_playlist["settings"]["show_live"] is True:
                self.loadLive()
            else:
                self.close()

        elif self.setup_title == _("Choose Live Categories"):
            self.close()

    def keyGreen(self):
        if self.setup_title == _("Choose Live Categories"):
            if glob.current_playlist["settings"]["show_vod"] is True:
                self.loadVod()
            elif glob.current_playlist["settings"]["show_series"] is True:
                self.loadSeries()
            else:
                self.save()

        elif self.setup_title == _("Choose VOD Categories"):
            if glob.current_playlist["settings"]["show_series"] is True:
                self.loadSeries()
            else:
                self.save()

        elif self.setup_title == _("Choose Series Categories"):
            self.save()

    def save(self):
        self.updateJson()
        from . import buildbouquets

        self.session.openWithCallback(self.exit, buildbouquets.BmxBuildBouquets)

    def exit(self, answer=None):
        if glob.finished:
            self.close(True)

    def updateJson(self, answer=None):
        self.playlists_all = bmx.getPlaylistJson()

        # print("*** glob ***", glob.current_playlist["data"]["series_streams"])

        if self.playlists_all:
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:
                    playlists["data"]["live_categories"] = glob.current_playlist["data"]["live_categories"]
                    playlists["data"]["vod_categories"] = glob.current_playlist["data"]["vod_categories"]
                    playlists["data"]["series_categories"] = glob.current_playlist["data"]["series_categories"]

                    playlists["data"]["live_streams"] = []
                    playlists["data"]["vod_streams"] = []
                    playlists["data"]["series_streams"] = []

                    playlists["data"]["live_categories_hidden"] = glob.current_playlist["data"]["live_categories_hidden"]
                    playlists["data"]["vod_categories_hidden"] = glob.current_playlist["data"]["vod_categories_hidden"]
                    playlists["data"]["series_categories_hidden"] = glob.current_playlist["data"]["series_categories_hidden"]

                    playlists["data"]["live_streams_hidden"] = glob.current_playlist["data"]["live_streams_hidden"]
                    playlists["data"]["vod_streams_hidden"] = glob.current_playlist["data"]["vod_streams_hidden"]
                    playlists["data"]["series_streams_hidden"] = glob.current_playlist["data"]["series_streams_hidden"]

                    break

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
