#!/usr/bin/python
# ~ # -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, skin_directory, version, pythonVer, dir_tmp

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap
from unicodedata import normalize

import os
import re

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
            if playlist["playlist_info"]["bouquet"] and playlist["playlist_info"]["playlist_type"] == "xtream":
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

        for x in selected_bouquet_list:
            url = str(x[3]) + "&action=get_live_streams"
            self.unique_ref = 0

            for playlist in self.playlists_all:
                if playlist.get("playlist_info", {}).get("bouquet") and \
                   playlist.get("playlist_info", {}).get("playlist_type") == "xtream" and \
                   playlist.get("playlist_info", {}).get("player_api") == x[3]:
                    glob.current_playlist = playlist
                    break

            stream_type = glob.current_playlist.get("settings", {}).get("live_type", "")
            full_url = glob.current_playlist.get("playlist_info", {}).get("full_url", "")

            self.unique_ref = sum(ord(c) for c in str(full_url))

            self.deletePiconSet(str(self.unique_ref))
            response = bmx.downloadXtreamApi(url)

            if not response:
                continue

            self.live_streams = response
            self.picon_list = []

            for channel in self.live_streams:
                stream_id = str(channel.get("stream_id") or "")
                category_id = str(channel.get("category_id") or "")
                stream_icon = str(channel.get("stream_icon") or "")
                name = str(channel.get("name") or "")

                if not (stream_id and category_id and stream_icon and name):
                    continue

                if "http" not in stream_icon:
                    continue

                if any(domain in stream_icon for domain in self.domainblocking):
                    continue

                if channel.get("stream_type") != "live":
                    continue

                if category_id in glob.current_playlist.get("data", {}).get("live_categories_hidden", []) or \
                   stream_id in glob.current_playlist.get("data", {}).get("live_streams_hidden", []):
                    continue

                # Clean name
                name = name.replace(":", "").replace('"', "").strip("- ").strip()
                try:
                    bouquet_id1 = int(stream_id) // 65535
                    bouquet_id2 = int(stream_id) - bouquet_id1 * 65535
                except Exception:
                    continue

                custom_sid = ":0:1:{}:{}:{}:0:0:0:0:".format(
                    format(bouquet_id1, "x"),
                    format(bouquet_id2, "x"),
                    format(self.unique_ref, "x")
                )

                custom_sid_from_channel = str(channel.get("custom_sid") or "")
                if custom_sid_from_channel not in ("null", "None", "0", ":0:0:0:0:0:0:0:0:0:") and len(custom_sid_from_channel) > 16:
                    custom_sid = custom_sid_from_channel
                    if custom_sid[0].isdigit():
                        custom_sid = custom_sid[1:]

                custom_sid = (stream_type + custom_sid).rstrip(":").replace(":", "_").upper()

                piconname = name
                if cfg.picon_type.value != "SRP":
                    try:
                        if pythonVer == 2:
                            piconname = normalize("NFKD", unicode(piconname, "utf-8", errors="ignore")).encode("ASCII", "ignore")
                        else:
                            piconname = normalize("NFKD", piconname).encode("ASCII", "ignore").decode()
                    except Exception:
                        pass

                    piconname = re.sub("[^a-z0-9]", "", piconname.replace("&", "and").replace("+", "plus").replace("*", "star").lower())

                # Append to list
                if cfg.picon_type.value == "SRP":
                    self.picon_list.append([piconname if cfg.picon_type.value != "SRP" else custom_sid, stream_icon])
                else:
                    if all(sublist[0] != piconname for sublist in self.picon_list):
                        self.picon_list.append([piconname, stream_icon])

            # Write temp list
            path = os.path.join(dir_tmp(), 'bmxpiconlist.txt')
            with open(path, 'w+') as f:
                for item in self.picon_list:
                    f.write("%s\n" % item)

            from . import downloadpicons
            self.session.openWithCallback(self.finished, downloadpicons.BmxDownloadPicons, self.picon_list)

    def finished(self, answer=None):
        try:
            self.close()
        except:
            pass
