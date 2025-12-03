#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import parsem3u
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, playlists_json, skin_directory, debugs, dir_etc

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

            self.live_categories_api = self.player_api + "&action=get_live_categories"
            self.vod_categories_api = self.player_api + "&action=get_vod_categories"
            self.series_categories_api = self.player_api + "&action=get_series_categories"

            self.live_streams_api = self.player_api + "&action=get_live_streams"
            self.vod_streams_api = self.player_api + "&action=get_vod_streams"
            self.series_streams_api = self.player_api + "&action=get_series"

        elif glob.current_playlist["playlist_info"]["playlist_type"] == "external":
            self.external_url = glob.current_playlist["playlist_info"]["full_url"]

        elif glob.current_playlist["playlist_info"]["playlist_type"] == "local":
            self.local_file = glob.current_playlist["playlist_info"]["full_url"]

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
        if debugs:
            print("*** start ***")

        self.timer = eTimer()

        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(10, True)

    def makeUrlList(self):
        if debugs:
            print("*** makeUrlList ***")

        try:
            self["splash"].hide()
        except:
            pass

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if glob.current_playlist["settings"]["show_live"]:
                self.downloadXtreamLive()
            elif glob.current_playlist["settings"]["show_vod"]:
                self.downloadXtreamVod()
            elif glob.current_playlist["settings"]["show_series"]:
                self.downloadXtreamSeries()
        elif glob.current_playlist["playlist_info"]["playlist_type"] == "external":
            self.downloadExternal()
        elif glob.current_playlist["playlist_info"]["playlist_type"] == "local":
            self.parseLocal()

    def downloadXtreamLive(self):
        if debugs:
            print("*** downloadXtreamLive ***")

        self.level = 1
        self.live_categories = []
        self.live_streams = []

        try:
            self["splash"].show()
        except:
            pass

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
                            "name": item.get("name", ""),
                            "stream_id": item.get("stream_id", ""),
                            "stream_icon": item.get("stream_icon", ""),
                            "epg_channel_id": item.get("epg_channel_id", ""),
                            "added": item.get("added", 0),  # Default to 0 for numeric
                            "category_id": item.get("category_id", ""),
                            "custom_sid": item.get("custom_sid", ""),
                            "tv_archive": item.get("tv_archive", 0),
                        }
                        for item in response if all(k in item for k in [
                            "name", "stream_id", "stream_icon", "epg_channel_id",
                            "added", "category_id", "custom_sid", "tv_archive"
                        ])
                    )
                    self.live_streams = list(response)
                response = None

        try:
            self["splash"].hide()
        except:
            pass

        self.loadLive()

    def downloadXtreamVod(self):
        if debugs:
            print("*** downloadXtreamVod ***")

        self.level = 1
        self.vod_categories = []
        self.vod_streams = []

        try:
            self["splash"].show()
        except:
            pass

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
                            "name": item.get("name", ""),
                            "stream_id": item.get("stream_id", ""),
                            "added": item.get("added", 0),
                            "category_id": item.get("category_id", ""),
                            "container_extension": item.get("container_extension", "")
                        }
                        for item in response if all(k in item for k in [
                            "name", "stream_id", "added", "category_id", "container_extension"
                        ])
                    )
                    self.vod_streams = list(response)

                response = None

        try:
            self["splash"].hide()
        except:
            pass

        self.loadVod()

    def downloadXtreamSeries(self):
        if debugs:
            print("*** downloadXtreamSeries ***")

        self.level = 1
        self.series_categories = []
        self.series_streams = []

        try:
            self["splash"].show()
        except:
            pass

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
                            "name": item.get("name", ""),
                            "series_id": item.get("series_id", ""),
                            "last_modified": item.get("last_modified", "0"),
                            "category_id": item.get("category_id", "")
                        }
                        for item in response if all(k in item for k in [
                            "name", "series_id", "last_modified", "category_id"
                        ])
                    )
                    self.series_streams = list(response)
                response = None

        try:
            self["splash"].hide()
        except:
            pass

        self.loadSeries()

    def downloadExternal(self):
        if debugs:
            print("*** downloadExternal ***")

        self.level = 1

        try:
            self["splash"].show()
        except:
            pass

        response = bmx.downloadM3U8File(self.external_url)

        if response:
            self.parseFullM3u8Data(response)
            response = None

        try:
            self["splash"].hide()
        except:
            pass

        self.loadLive()

    def parseLocal(self):
        if debugs:
            print("*** parseLocal (load local file) ***")

        self.level = 1

        try:
            self["splash"].show()
        except:
            pass

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

        try:
            self["splash"].hide()
        except:
            pass

        self.loadLive()

    def loadLive(self):
        if debugs:
            print("*** loadlive ***")

        self.level = 1

        self.setup_title = _("Choose Live Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["settings"]["show_live"] and self.live_categories and self.live_streams:
            self.category_list = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["show_vod"] or glob.current_playlist["settings"]["show_series"]:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in self.live_categories:

                if str(category["category_id"]) in glob.current_playlist["data"]["live_categories_hidden"] or \
                   str(category["category_name"]) in glob.current_playlist["data"]["live_categories_hidden"]:
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

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_vod"]:
                    self.downloadXtreamVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.downloadXtreamSeries()
            else:
                if glob.current_playlist["settings"]["show_vod"]:
                    self.loadVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.loadSeries()

    def loadVod(self):
        if debugs:
            print("*** loadVod ***")

        self.level = 2

        self.setup_title = _("Choose VOD Categories")
        self.setTitle(self.setup_title)

        if glob.current_playlist["settings"]["show_vod"] and self.vod_categories and self.vod_streams:
            self.category_list = []
            self.categorySelectedList = []

            if glob.current_playlist["settings"]["show_series"]:
                self["key_green"].setText(_("Next"))
            else:
                self["key_green"].setText(_("Create"))

            for category in self.vod_categories:
                if str(category["category_id"]) in glob.current_playlist["data"]["vod_categories_hidden"] or \
                   str(category["category_name"]) in glob.current_playlist["data"]["vod_categories_hidden"]:
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

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_vod"]:
                    self.downloadXtreamVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.downloadXtreamSeries()

            else:
                if glob.current_playlist["settings"]["show_vod"]:
                    self.loadVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.loadSeries()

    def loadSeries(self):
        if debugs:
            print("*** loadSeries ***")

        self.level = 3

        self.setup_title = _("Choose Series Categories")
        self.setTitle(self.setup_title)

        self.category_list = []
        self.categorySelectedList = []

        self["key_green"].setText(_("Create"))

        if glob.current_playlist["settings"]["show_series"] and self.series_categories and self.series_streams:
            for category in self.series_categories:
                if str(category["category_id"]) in glob.current_playlist["data"]["series_categories_hidden"] or \
                        str(category["category_name"]) in glob.current_playlist["data"]["series_categories_hidden"]:
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
            glob.current_playlist["settings"]["show_series"] = False
            self.save()

    def selectionChanged(self):
        if debugs:
            print("*** selectionChanged ***")

        self["list2"].setList([])
        self.channel_list = []
        self.channel_selected_list = []

        if not self["list1"].getCurrent():
            return

        if self["list1"].getCurrent()[3]:
            self["list2"].setList([])
            return

        category = self["list1"].getCurrent()[2]

        if self.level == 1:
            for channel in self.live_streams:

                name = str(channel.get("name", ""))
                stream_id = str(channel.get("stream_id", ""))
                added = str(channel.get("added", "0"))

                if not name or not stream_id:
                    continue

                if channel["category_id"] == category:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        if stream_id in glob.current_playlist["data"]["live_streams_hidden"] or name in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([stream_id, name, True, added])
                        else:
                            self.channel_selected_list.append([stream_id, name, False, added])
                    else:
                        if stream_id in glob.current_playlist["data"]["live_streams_hidden"] or name in glob.current_playlist["data"]["live_streams_hidden"]:
                            self.channel_selected_list.append([stream_id, name, True, "0"])
                        else:
                            self.channel_selected_list.append([stream_id, name, False, "0"])

            if glob.current_playlist["settings"]["live_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["live_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 2:
            for channel in self.vod_streams:

                name = str(channel.get("name", ""))
                stream_id = str(channel.get("stream_id", ""))
                added = str(channel.get("added", "0"))

                if not name or not stream_id:
                    continue

                if channel["category_id"] == category:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        if stream_id in glob.current_playlist["data"]["vod_streams_hidden"] or name in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([stream_id, name, True, added])
                        else:
                            self.channel_selected_list.append([stream_id, name, False, added])
                    else:
                        if stream_id in glob.current_playlist["data"]["vod_streams_hidden"] or name in glob.current_playlist["data"]["vod_streams_hidden"]:
                            self.channel_selected_list.append([stream_id, name, True, "0"])
                        else:
                            self.channel_selected_list.append([stream_id, name, False, "0"])

            if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        elif self.level == 3:
            for channel in self.series_streams:

                name = str(channel.get("name", ""))
                series_id = str(channel.get("series_id", ""))
                last_modified = str(channel.get("last_modified", "0"))

                if not name or not series_id:
                    continue

                if channel["category_id"] == category:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        if series_id in glob.current_playlist["data"]["series_streams_hidden"] or name in glob.current_playlist["data"]["series_streams_hidden"]:
                            self.channel_selected_list.append([series_id, name, True, last_modified])
                        else:
                            self.channel_selected_list.append([series_id, name, False, last_modified])
                    else:
                        if series_id in glob.current_playlist["data"]["series_streams_hidden"] or name in glob.current_playlist["data"]["series_streams_hidden"]:
                            self.channel_selected_list.append([series_id, name, True, "0"])
                        else:
                            self.channel_selected_list.append([series_id, name, False, "0"])

            if glob.current_playlist["settings"]["vod_stream_order"] == "alphabetical":
                self.channel_selected_list.sort(key=lambda x: x[1].lower())

            if glob.current_playlist["settings"]["vod_stream_order"] == "added":
                self.channel_selected_list.sort(key=lambda x: x[3].lower(), reverse=True)

        if self.setup_title != _("Choose Series Categories"):
            self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
        else:
            self.channel_list = [self.buildListEntry2(x[0], x[1], x[2]) for x in self.channel_selected_list]
        self["list2"].setList(self.channel_list)

    def buildListEntry(self, id, name, hidden):
        if hidden:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_hidden.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        return (pixmap, str(name), str(id), hidden)

    def buildListEntry2(self, id, name, hidden):
        pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_disabled.png"))
        return (pixmap, str(name), str(id), hidden)

    def refresh(self):
        if debugs:
            print("*** refresh ***")

        def update_hidden_list(selected_list, hidden_list, category_type):
            for hidden in selected_list:
                key = hidden[0] if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream" else hidden[1]

                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                    key = hidden[0]
                else:
                    key = hidden[1]
                if self.setup_title == _("Choose Series Categories"):
                    key = hidden[1]

                if hidden[2]:
                    if key not in hidden_list:
                        hidden_list.append(key)
                elif key in hidden_list:
                    hidden_list.remove(key)

        if self.selected_list == self["list1"]:
            if self["list1"].getCurrent():
                self.category_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.categorySelectedList]
                self["list1"].updateList(self.category_list)

                if self.setup_title == _("Choose Live Categories"):
                    update_hidden_list(self.categorySelectedList, glob.current_playlist["data"]["live_categories_hidden"], "live")

                elif self.setup_title == _("Choose VOD Categories"):
                    update_hidden_list(self.categorySelectedList, glob.current_playlist["data"]["vod_categories_hidden"], "vod")

                elif self.setup_title == _("Choose Series Categories"):
                    update_hidden_list(self.categorySelectedList, glob.current_playlist["data"]["series_categories_hidden"], "series")

                if self["list1"].getCurrent()[3]:
                    self["list2"].setList([])
                else:
                    self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                    self["list2"].updateList(self.channel_list)

                self.selectionChanged()

        if self.selected_list == self["list2"]:
            if self["list1"].getCurrent():
                self.channel_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.channel_selected_list]
                self["list2"].updateList(self.channel_list)

                if self.setup_title == _("Choose Live Categories"):
                    update_hidden_list(self.channel_selected_list, glob.current_playlist["data"]["live_streams_hidden"], "live")

                elif self.setup_title == _("Choose VOD Categories"):
                    update_hidden_list(self.channel_selected_list, glob.current_playlist["data"]["vod_streams_hidden"], "vod")

                elif self.setup_title == _("Choose Series Categories"):
                    update_hidden_list(self.channel_selected_list, glob.current_playlist["data"]["series_streams_hidden"], "series")

    def toggleSelection(self):
        if self.setup_title == _("Choose Series Categories") and self.current_list == 2:
            return
        if len(self[self.active].list) > 0:
            idx = self[self.active].getIndex()

            if self.selected_list == self["list1"] and self["list1"].getCurrent():
                self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

            elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def toggleAllSelection(self):
        if self.setup_title == _("Choose Series Categories") and self.current_list == 2:
            return
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = not self.categorySelectedList[idx][2]

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = not self.channel_selected_list[idx][2]
        self.refresh()

    def clearAllSelection(self):
        if self.setup_title == _("Choose Series Categories") and self.current_list == 2:
            return
        if len(self[self.active].list) > 0:
            for idx, item in enumerate(self[self.active].list):
                if self.selected_list == self["list1"] and self["list1"].getCurrent():
                    self.categorySelectedList[idx][2] = False

                elif self.selected_list == self["list2"] and self["list2"].getCurrent():
                    self.channel_selected_list[idx][2] = False
        self.refresh()

    def keyCancel(self):
        if self.setup_title == _("Choose Series Categories"):

            self.updateJson("series")

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_vod"]:
                    self.downloadXtreamVod()
                elif glob.current_playlist["settings"]["show_live"]:
                    self.downloadXtreamLive()
                else:
                    self.close()

            else:
                if glob.current_playlist["settings"]["show_vod"]:
                    self.loadVod()
                elif glob.current_playlist["settings"]["show_live"]:
                    self.loadLive()
                else:
                    self.close()

        elif self.setup_title == _("Choose VOD Categories"):

            self.updateJson("vod")

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_live"]:
                    self.downloadXtreamLive()
                else:
                    self.close()

            else:
                if glob.current_playlist["settings"]["show_live"]:
                    self.loadLive()
                else:
                    self.close()

        elif self.setup_title == _("Choose Live Categories"):
            self.updateJson("live")
            self.close()

    def keyGreen(self):
        if self.setup_title == _("Choose Live Categories"):

            self.updateJson("live")

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_vod"]:
                    self.downloadXtreamVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.downloadXtreamSeries()
                else:
                    self.save()

            else:
                if glob.current_playlist["settings"]["show_vod"]:
                    self.loadVod()
                elif glob.current_playlist["settings"]["show_series"]:
                    self.loadSeries()
                else:
                    self.save()

        elif self.setup_title == _("Choose VOD Categories"):

            self.updateJson("vod")

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                if glob.current_playlist["settings"]["show_series"]:
                    self.downloadXtreamSeries()
                else:
                    self.save()

            else:
                if glob.current_playlist["settings"]["show_series"]:
                    self.loadSeries()
                else:
                    self.save()

        elif self.setup_title == _("Choose Series Categories"):
            self.updateJson("series")
            self.save()

    def save(self):
        from . import buildbouquets
        self.session.openWithCallback(self.exit, buildbouquets.BmxBuildBouquets)

    def exit(self, answer=None):
        if glob.finished:
            self.close(True)

    def updateJson(self, answer=None):
        if debugs:
            print("*** updateJson ***")

        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            for index, playlists in enumerate(self.playlists_all):
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:
                    if answer == "live":
                        playlists["data"]["live_categories_hidden"] = glob.current_playlist["data"]["live_categories_hidden"]
                        playlists["data"]["live_streams_hidden"] = glob.current_playlist["data"]["live_streams_hidden"]

                    elif answer == "vod":
                        playlists["data"]["vod_categories_hidden"] = glob.current_playlist["data"]["vod_categories_hidden"]
                        playlists["data"]["vod_streams_hidden"] = glob.current_playlist["data"]["vod_streams_hidden"]

                    elif answer == "series":
                        playlists["data"]["series_categories_hidden"] = glob.current_playlist["data"]["series_categories_hidden"]
                        playlists["data"]["series_streams_hidden"] = glob.current_playlist["data"]["series_streams_hidden"]
                    break

        self.clearCaches()

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f, indent=4)

    def clearCaches(self):
        if debugs:
            print("*** clearcaches ***")

        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

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
