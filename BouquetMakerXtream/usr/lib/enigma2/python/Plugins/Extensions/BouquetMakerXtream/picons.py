#!/usr/bin/python
# ~ # -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, skin_directory, version, pythonVer

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import os
import re
import unicodedata

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
        self["list"] = List(self.draw_list, enableWrapAround=True)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Download"))
        self["key_yellow"] = StaticText("")
        self["key_blue"] = StaticText("")
        self["key_info"] = StaticText("")
        self["version"] = StaticText("")

        self.playlists_all = bmx.getPlaylistJson()

        self.domainblocking = [
            "http://logourl.net"
        ]

        self.onLayoutFinish.append(self.__layoutFinished)

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.keyCancel,
            "green": self.downloadPicons,
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
            index = self["list"].getIndex()
            for idx, item in enumerate(self["list"].list):
                if idx != index:
                    self.start_list[idx][2] = False
            self.start_list[index][2] = not self.start_list[index][2]
            self.refresh()

    def getSelectionsList(self):
        return [item for item in self.start_list if item[2]]

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

            stream_type = glob.current_playlist["settings"]["live_type"]

            full_url = glob.current_playlist["playlist_info"]["full_url"]
            self.unique_ref = 0

            for j in str(full_url):
                value = ord(j)
                self.unique_ref += value

            self.deletePiconSet(str(self.unique_ref))

            response = bmx.downloadApi(url)

            if response:
                self.live_streams = response
                x = 0
                self.picon_list = []
                for channel in self.live_streams:

                    if int(cfg.max_live.value) != 0 and x > int(cfg.max_live.value):
                        break

                    if "stream_id" in channel and channel["stream_id"]:
                        stream_id = str(channel["stream_id"])
                    else:
                        continue

                    if "category_id" not in channel or not channel["category_id"]:
                        continue

                    if "stream_icon" not in channel or not channel["stream_icon"]:
                        continue
                    else:
                        stream_icon = str(channel["stream_icon"])

                    if "http" not in stream_icon:
                        continue

                    blocked = False

                    for domain in self.domainblocking:
                        if domain in stream_icon:
                            blocked = True

                    """
                    if " " in stream_icon or "%20" in stream_icon:
                        continue
                        """

                    if blocked:
                        continue

                    if channel["stream_type"] != "live":
                        continue

                    custom_sid = ""

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["live_streams_hidden"]:
                        if "name" in channel and channel["name"]:
                            name = channel["name"]
                            name = name.replace(":", "").replace('"', "").strip("-")
                        else:
                            continue

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        custom_sid = ":0:1:" + str(format(bouquet_id1, "x")) + ":" + str(format(bouquet_id2, "x")) + ":" + str(format(self.unique_ref, "x")) + ":0:0:0:0:"

                        if "custom_sid" in channel and channel["custom_sid"]:
                            if channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None and channel["custom_sid"] != "0":
                                if channel["custom_sid"][0].isdigit():
                                    channel["custom_sid"] = channel["custom_sid"][1:]

                                custom_sid = channel["custom_sid"]

                        custom_sid = str(stream_type) + str(custom_sid).rstrip(":")
                        custom_sid = custom_sid.replace(":", "_")
                        custom_sid = custom_sid.upper()

                        if "epg_channel_id" in channel and channel["epg_channel_id"]:
                            channel_id = str(channel["epg_channel_id"])
                            if "&" in channel_id:
                                channel_id = channel_id.replace("&", "&amp;")

                        piconname = name

                        if cfg.picon_type.value == "SRP":
                            self.picon_list.append([custom_sid, stream_icon])
                        else:
                            try:
                                if pythonVer == 2:
                                    piconname = unicodedata.normalize("NFKD", unicode(str(piconname), "utf_8", errors="ignore")).encode("ASCII", "ignore")

                                elif pythonVer == 3:
                                    piconname = unicodedata.normalize("NFKD", piconname).encode("ASCII", "ignore").decode()
                            except:
                                pass

                            piconname = re.sub("[^a-z0-9]", "", piconname.replace("&", "and").replace("+", "plus").replace("*", "star").lower())

                            if piconname and stream_icon:
                                if cfg.picon_type.value == "SRP":
                                    self.picon_list.append([piconname, stream_icon])
                                else:
                                    exists = False
                                    for sublist in self.picon_list:
                                        if str(sublist[0]) == str(piconname):
                                            exists = True
                                            break
                                    if exists is False:
                                        self.picon_list.append([piconname, stream_icon])

                x += 1

                # self.picon_list.sort(key=lambda x: x[1])

                with open('/tmp/bmxpiconlist.txt', 'w+') as f:
                    for item in self.picon_list:
                        f.write("%s\n" % item)
                    f.truncate()

                from . import downloadpicons
                self.session.openWithCallback(self.finished, downloadpicons.BmxDownloadPicons, self.picon_list)

    def finished(self, answer=None):
        try:
            self.close()
        except:
            pass
