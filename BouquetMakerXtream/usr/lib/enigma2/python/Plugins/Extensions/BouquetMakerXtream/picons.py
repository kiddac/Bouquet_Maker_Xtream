#!/usr/bin/python
# ~ # -*- coding: utf-8 -*-

import os
import re
import unicodedata

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from . import _
from . import bouquet_globals as glob
from . import downloadpicons
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, skin_directory, version, pythonVer

if pythonVer == 3:
    unicode = str


class BmxDownloadPicons(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "bouquets.xml")
        with open(skin, "r") as f:
            self.skin = f.read()
        self.setup_title = _("Download Picons")

        # new list code
        self.start_list = []
        self.draw_list = []
        self["list"] = List(self.draw_list)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Download"))
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Clear All"))
        self["key_info"] = StaticText("")
        self["version"] = StaticText("")

        self.playlists_all = bmx.getPlaylistJson()

        self.onLayoutFinish.append(self.__layoutFinished)

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.keyCancel,
            "green": self.downloadPicons,
            "yellow": self.toggleAllSelection,
            "blue": self.clearAllSelection,
            "cancel": self.keyCancel,
            "ok": self.toggleSelection
        }, -2)

        self["version"].setText(version)

        self.getStartList()
        self.refresh()

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def buildListEntry(self, name, index, selected, player_api):
        if selected:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_off.png"))
        return (pixmap, str(name), index, selected, player_api)

    def getStartList(self):
        for playlist in self.playlists_all:
            if playlist["playlist_info"]["bouquet"] is True and playlist["playlist_info"]["playlist_type"] == "xtream":
                self.start_list.append([str(playlist["playlist_info"]["name"]), playlist["playlist_info"]["index"], False,  playlist["playlist_info"]["player_api"]])

        self.draw_list = [self.buildListEntry(x[0], x[1], x[2], x[3]) for x in self.start_list]
        self["list"].setList(self.draw_list)

    def refresh(self):
        self.draw_list = []
        self.draw_list = [self.buildListEntry(x[0], x[1], x[2], x[3]) for x in self.start_list]
        self["list"].updateList(self.draw_list)

    def toggleSelection(self):
        if len(self["list"].list) > 0:
            idx = self["list"].getIndex()
            self.start_list[idx][2] = not self.start_list[idx][2]
            self.refresh()

    def toggleAllSelection(self):
        for idx, item in enumerate(self["list"].list):
            self.start_list[idx][2] = not self.start_list[idx][2]
        self.refresh()

    def getSelectionsList(self):
        return [item for item in self.start_list if item[2]]

    def clearAllSelection(self):
        for idx, item in enumerate(self["list"].list):
            self.start_list[idx][2] = False
        self.refresh()

    def keyCancel(self):
        self.close()

    def deletePiconSet(self, unique):
        pass

    def downloadPicons(self):
        selected_bouquet_list = self.getSelectionsList()

        response = []

        for x in selected_bouquet_list:
            url = str(x[3]) + "&action=get_live_streams"
            self.unique_ref = 0

            for playlist in self.playlists_all:
                if playlist["playlist_info"]["player_api"] == x[3]:
                    glob.current_playlist = playlist
                    break

            self.deletePiconSet(str(self.unique_ref))

            stream_type = glob.current_playlist["settings"]["live_type"]

            full_url = glob.current_playlist["playlist_info"]["full_url"]
            self.unique_ref = 0

            for j in str(full_url):
                value = ord(j)
                self.unique_ref += value

            response = bmx.downloadUrl(url, "json")

            if response:
                self.live_streams = response
                x = 0
                self.picon_list = []
                for channel in self.live_streams:

                    custom_sid = ""

                    if cfg.max_live.value != 0 and x > cfg.max_live.value:
                        break

                    stream_id = str(channel["stream_id"])

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["live_streams_hidden"]:
                        name = channel["name"]
                        name = name.replace(":", "").replace('"', "").strip("-")

                        channel_id = str(channel["epg_channel_id"])
                        if channel_id and "&" in channel_id:
                            channel_id = channel_id.replace("&", "&amp;")

                        piconname = name

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"

                        if "custom_sid" in channel:
                            if channel["custom_sid"] and channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None and channel["custom_sid"] != "0":
                                if channel["custom_sid"][0].isdigit():
                                    channel["custom_sid"] = channel["custom_sid"][1:]

                                custom_sid = channel["custom_sid"]

                        custom_sid = str(stream_type) + str(custom_sid).rstrip(":")
                        custom_sid = custom_sid.replace(":", "_")
                        custom_sid = custom_sid.upper()

                        if channel["stream_icon"] and "http" in channel["stream_icon"] \
                                and ("png" in channel["stream_icon"].lower() or "jpg" in channel["stream_icon"].lower() or "jpeg" in channel["stream_icon"].lower()):

                            if cfg.picon_type.value == "SRP":
                                self.picon_list.append([custom_sid, channel["stream_icon"]])
                            else:
                                if pythonVer == 2:
                                    piconname = unicodedata.normalize("NFKD", unicode(piconname, "utf_8", errors="ignore")).encode("ASCII", "ignore")
                                elif pythonVer == 3:
                                    piconname = unicodedata.normalize("NFKD", piconname).encode("ASCII", "ignore").decode("ascii")

                                    piconname = re.sub("[^a-z0-9]", "", piconname.replace("&", "and").replace("+", "plus").replace("*", "star").lower())

                                self.picon_list.append([piconname, channel["stream_icon"]])
                            x += 1

                # self.picon_list.sort(key=lambda x: x[1])
                """
                with open('/tmp/bmxpiconlist.txt', 'w+') as f:
                    for item in self.picon_list:
                        f.write("%s\n" % item)
                        """

                self.session.openWithCallback(self.finished, downloadpicons.BmxDownloadPicons, self.picon_list)

    def finished(self):
        self.session.openWithCallback(self.close, MessageBox, "Finished.\n\nRestart your GUI if downloaded to picons folder.\n\nYour created picons can be found in \n" + str(cfg.picon_location.value), MessageBox.TYPE_INFO, timeout=10)
