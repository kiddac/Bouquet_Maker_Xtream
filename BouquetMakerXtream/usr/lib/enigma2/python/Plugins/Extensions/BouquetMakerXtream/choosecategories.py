#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, COMMON_PATH, HAS_CONCURRENT, HAS_MULTIPROCESSING, PLAYLISTS_JSON, SKIN_DIRECTORY, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


class BmxChooseCategories(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "categories.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()

        self.setup_title = ""

        self.category_list = []
        self.channel_list = []

        self.level = 1
        self.data = False

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
            "ok": self.toggle_selection,
            "red": self.key_cancel,
            "cancel": self.key_cancel,
            "green": self.keyGreen,
            "yellow": self.toggle_all_selection,
            "blue": self.clear_all_selection,
            "left": self.go_left,
            "right": self.go_right,
            "channelUp": self.page_up,
            "channelDown": self.page_down,
            "2": self.page_up,
            "8": self.page_down,
            "up": self.go_up,
            "down": self.go_down,
        }, -2)

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            self.player_api = glob.CURRENT_PLAYLIST["playlist_info"]["player_api"]
            self.p_live_streams_url = self.player_api + "&action=get_live_streams"
            self.p_vod_streams_url = self.player_api + "&action=get_vod_streams"
            self.p_series_streams_url = self.player_api + "&action=get_series"

        self.onFirstExecBegin.append(self.start)

    def enable_list(self):
        self["list2"].master.master.instance.setSelectionEnable(0)
        self.active = "list" + str(self.current_list)

        if self[self.active].getCurrent():
            self[self.active].master.master.instance.setSelectionEnable(1)
            self.selected_list = self[self.active]
            if self.selected_list == self["list2"]:
                self.selected_list.setIndex(0)
            return True
        else:
            return False

    def go_left(self):
        success = False
        if self.selected_list.getCurrent():
            while success is False:
                self.current_list -= 1
                if self.current_list < 1:
                    self.current_list = 2
                success = self.enable_list()

    def go_right(self):
        success = False
        if self.selected_list.getCurrent():
            while success is False:
                self.current_list += 1
                if self.current_list > 2:
                    self.current_list = 1
                success = self.enable_list()

    def page_up(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.pageUp)

            if self.selected_list == self["list1"]:
                self.selection_changed()

    def page_down(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.pageDown)

            if self.selected_list == self["list1"]:
                self.selection_changed()

    def go_up(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.moveUp)

            if self.selected_list == self["list1"]:
                self.selection_changed()

    def go_down(self):
        if self.selected_list.getCurrent():
            instance = self.selected_list.master.master.instance
            instance.moveSelection(instance.moveDown)

            if self.selected_list == self["list1"]:
                self.selection_changed()

    def start(self):
        try:
            self.timer_conn = self.timer.timeout.connect(self.make_url_list)
        except Exception:
            try:
                self.timer.callback.append(self.make_url_list)
            except Exception:
                self.make_url_list()
        self.timer.start(5, True)

    def make_url_list(self):
        # print("*** make_url_list ***")
        self.live_url_list = []
        self.vod_url_list = []
        self.series_url_list = []
        self.external_url_list = []

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "local":
            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                if glob.CURRENT_PLAYLIST["settings"]["show_live"] is True:
                    self.live_url_list.append([self.p_live_streams_url, 3, "json"])

                if glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
                    self.vod_url_list.append([self.p_vod_streams_url, 4, "json"])

                if glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                    self.series_url_list.append([self.p_series_streams_url, 5, "json"])

        try:
            self["splash"].hide()
        except:
            pass

        if glob.CURRENT_PLAYLIST["settings"]["show_live"] is True:
            self.load_live()
        elif glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
            self.load_vod()
        elif glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
            self.load_series()

    def process_downloads(self, stream_type):
        # print("*** process_downloads ***")

        if stream_type == "live":
            self.url_list = self.live_url_list

        if stream_type == "vod":
            self.url_list = self.vod_url_list

        if stream_type == "series":
            self.url_list = self.series_url_list

        if stream_type == "external":
            self.url_list = self.external_url_list

        try:
            self["splash"].show()
        except:
            pass

        results = ""

        threads = min(len(self.url_list), 10)

        if HAS_CONCURRENT or HAS_MULTIPROCESSING:
            if HAS_CONCURRENT:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(bmx.download_url_multi, self.url_list)
                except Exception as e:
                    print(e)

            elif HAS_MULTIPROCESSING:
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
                    if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                        if category == 3:
                            glob.CURRENT_PLAYLIST["data"]["live_streams"] = response
                        elif category == 4:
                            glob.CURRENT_PLAYLIST["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.CURRENT_PLAYLIST["data"]["series_streams"] = response

        else:
            for url in self.url_list:
                result = bmx.download_url_multi(url)
                category = result[0]
                response = result[1]
                if response:
                    if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                        # add categories to main json file
                        if category == 3:
                            glob.CURRENT_PLAYLIST["data"]["live_streams"] = response
                        elif category == 4:
                            glob.CURRENT_PLAYLIST["data"]["vod_streams"] = response
                        elif category == 5:
                            glob.CURRENT_PLAYLIST["data"]["series_streams"] = response
        try:
            self["splash"].hide()
        except:
            pass

    def load_live(self):
        # print("*** load_live ***")
        self.level = 1
        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            self.process_downloads("live")

        self.setup_title = _("Choose Live Categories")
        self.setTitle(self.setup_title)

        if glob.CURRENT_PLAYLIST["data"]["live_categories"]:
            self.category_list = []
            self.categorySelectedList = []

            if glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True or glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.CURRENT_PLAYLIST["data"]["live_categories"]:
                categorycount = len(category)

                if str(category["category_id"]) in glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True, categorycount, 0])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False, categorycount, 0])

            if glob.CURRENT_PLAYLIST["settings"]["live_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.categorySelectedList]

            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.data = True
            self.enable_list()
            self.selection_changed()
        else:
            glob.CURRENT_PLAYLIST["settings"]["show_live"] = False
            if glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
                self.load_vod()
            elif glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self.load_series()

    def load_vod(self):
        self.level = 2
        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            self.process_downloads("vod")

        self.setup_title = _("Choose VOD Categories")
        self.setTitle(self.setup_title)

        if glob.CURRENT_PLAYLIST["data"]["vod_categories"]:
            self.category_list = []
            self.categorySelectedList = []

            if glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in glob.CURRENT_PLAYLIST["data"]["vod_categories"]:
                if str(category["category_id"]) in glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if glob.CURRENT_PLAYLIST["settings"]["vod_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.data = True
            self.enable_list()
            self.selection_changed()

        else:
            glob.CURRENT_PLAYLIST["settings"]["show_vod"] = False
            if glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self.load_series()

    def load_series(self):
        self.level = 3
        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            self.process_downloads("series")

        self.setup_title = _("Choose Series Categories")
        self.setTitle(self.setup_title)

        self.category_list = []
        self.categorySelectedList = []

        self["key_green"].setText(_("Create"))

        if glob.CURRENT_PLAYLIST["data"]["series_categories"]:
            for category in glob.CURRENT_PLAYLIST["data"]["series_categories"]:
                if str(category["category_id"]) in glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"]:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), True])
                else:
                    self.categorySelectedList.append([str(category["category_id"]), str(category["category_name"]), False])

            if glob.CURRENT_PLAYLIST["settings"]["vod_category_order"] == "alphabetical":
                self.categorySelectedList.sort(key=lambda x: x[1].lower())

            self.category_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.categorySelectedList]
            self["list1"].setList(self.category_list)
            self["list1"].setIndex(0)
            self.current_list = 1
            self.data = True
            self.enable_list()
            self.selection_changed()
        else:
            self.save()

    def selection_changed(self):
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
            for channel in glob.CURRENT_PLAYLIST["data"]["live_streams"]:
                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if glob.CURRENT_PLAYLIST["settings"]["live_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.CURRENT_PLAYLIST["settings"]["live_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 2:
            for channel in glob.CURRENT_PLAYLIST["data"]["vod_streams"]:
                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["stream_id"]) in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, str(channel["added"])])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, str(channel["added"])])
                else:
                    if channel["category_id"] == category:
                        if str(channel["name"]) in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), True, "0"])
                        else:
                            self.channel_selected_list.append([str(channel["stream_id"]), str(channel["name"]), False, "0"])

            if glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 3:
            for channel in glob.CURRENT_PLAYLIST["data"]["series_streams"]:
                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                    if channel["category_id"] == category:
                        if str(channel["series_id"]) in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                            self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), True, str(channel["last_modified"])])
                        else:
                            self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), False, str(channel["last_modified"])])
                else:
                    if str(channel["name"]) in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                        self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), True, "0"])
                    else:
                        self.channel_selected_list.append([str(channel["series_id"]), str(channel["name"]), False, "0"])

            if glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        self.channel_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.channel_selected_list]
        self["list2"].setList(self.channel_list)
        self.current_list = 1
        self.enable_list()

    def build_list_entry(self, id, name, hidden):
        if hidden:
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "lock_hidden.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "lock_on.png"))
        return (pixmap, str(name), str(id), hidden)

    def refresh(self):
        if self.selected_list == self["list1"]:
            if self["list1"].getCurrent():
                self.category_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.categorySelectedList]
                self["list1"].updateList(self.category_list)

                if self.setup_title == (_("Choose Live Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"].remove(hidden[0])

                elif self.setup_title == (_("Choose VOD Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"].remove(hidden[0])

                elif self.setup_title == (_("Choose Series Categories")):
                    for hidden in self.categorySelectedList:
                        if hidden[2] is True:
                            if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"].append(hidden[0])
                        else:
                            if hidden[0] in glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"]:
                                glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"].remove(hidden[0])

                if self["list1"].getCurrent()[3] is True:
                    self["list2"].setList([])
                else:
                    self.channel_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                    self["list2"].updateList(self.channel_list)

                self.selection_changed()

        if self.selected_list == self["list2"]:
            if self["list1"].getCurrent():
                self.channel_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                self["list2"].updateList(self.channel_list)

                if self.setup_title == (_("Choose Live Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"].append(hidden[1])
                        else:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"].remove(hidden[1])

                elif self.setup_title == (_("Choose VOD Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"].append(hidden[1])
                        else:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"].remove(hidden[1])

                elif self.setup_title == (_("Choose Series Categories")):
                    for hidden in self.channel_selected_list:
                        if hidden[2] is True:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] not in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"].append(hidden[0])
                            else:
                                if hidden[1] not in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"].append(hidden[1])
                        else:
                            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                                if hidden[0] in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"].remove(hidden[0])
                            else:
                                if hidden[1] in glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]:
                                    glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"].remove(hidden[1])

    def toggle_selection(self):
        if len(self[self.active].list) > 0:
            idx = self[self.active].getIndex()

            if self.selected_list == self["list1"] and self["list1"].getCurrent():
                self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

            elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def toggle_all_selection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def clear_all_selection(self):
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = False

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = False
        self.refresh()

    def key_cancel(self):
        if self.setup_title == (_("Choose Series Categories")):
            if glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
                self.load_vod()
            elif glob.CURRENT_PLAYLIST["settings"]["show_live"] is True:
                self.load_live()
            else:
                self.close()

        elif self.setup_title == (_("Choose VOD Categories")):
            if glob.CURRENT_PLAYLIST["settings"]["show_live"] is True:
                self.load_live()
            else:
                self.close()

        elif self.setup_title == (_("Choose Live Categories")):
            self.close()

    def keyGreen(self):
        if self.setup_title == (_("Choose Live Categories")):
            if glob.CURRENT_PLAYLIST["settings"]["show_vod"] is True:
                self.load_vod()
            elif glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self.load_series()
            else:
                self.save()

        elif self.setup_title == (_("Choose VOD Categories")):
            if glob.CURRENT_PLAYLIST["settings"]["show_series"] is True:
                self.load_series()
            else:
                self.save()

        elif self.setup_title == (_("Choose Series Categories")):
            self.save()

    def save(self):
        self.update_json()
        from . import buildbouquets

        self.session.openWithCallback(self.exit, buildbouquets.BmxBuildBouquets)

    def exit(self, answer=None):
        if glob.FINISHED:
            self.close(True)

    def update_json(self, answer=None):
        self.playlists_all = bmx.get_playlist_json()

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.CURRENT_PLAYLIST["playlist_info"]["full_url"]:
                    self.playlists_all[x]["data"]["live_categories"] = glob.CURRENT_PLAYLIST["data"]["live_categories"]
                    self.playlists_all[x]["data"]["vod_categories"] = glob.CURRENT_PLAYLIST["data"]["vod_categories"]
                    self.playlists_all[x]["data"]["series_categories"] = glob.CURRENT_PLAYLIST["data"]["series_categories"]

                    self.playlists_all[x]["data"]["live_streams"] = []
                    self.playlists_all[x]["data"]["vod_streams"] = []
                    self.playlists_all[x]["data"]["series_streams"] = []

                    self.playlists_all[x]["data"]["live_categories_hidden"] = glob.CURRENT_PLAYLIST["data"]["live_categories_hidden"]
                    self.playlists_all[x]["data"]["vod_categories_hidden"] = glob.CURRENT_PLAYLIST["data"]["vod_categories_hidden"]
                    self.playlists_all[x]["data"]["series_categories_hidden"] = glob.CURRENT_PLAYLIST["data"]["series_categories_hidden"]

                    self.playlists_all[x]["data"]["live_streams_hidden"] = glob.CURRENT_PLAYLIST["data"]["live_streams_hidden"]
                    self.playlists_all[x]["data"]["vod_streams_hidden"] = glob.CURRENT_PLAYLIST["data"]["vod_streams_hidden"]
                    self.playlists_all[x]["data"]["series_streams_hidden"] = glob.CURRENT_PLAYLIST["data"]["series_streams_hidden"]

                    break
                x += 1

        with open(PLAYLISTS_JSON, "w", encoding="utf-8") as f:
            json.dump(self.playlists_all, f)
