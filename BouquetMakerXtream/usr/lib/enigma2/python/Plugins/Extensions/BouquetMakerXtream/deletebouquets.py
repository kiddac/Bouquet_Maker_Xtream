#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, common_path, epgimporter, playlists_json, skin_directory, version

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import json
import os


class BmxDeleteBouquets(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "bouquets.xml")
        with open(skin, "r") as f:
            self.skin = f.read()
        self.setup_title = _("Delete Bouquets")

        # new list code
        self.start_list = []
        self.draw_list = []
        self["list"] = List(self.draw_list, enableWrapAround=True)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Delete"))
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Clear All"))
        self["key_info"] = StaticText("")
        self["version"] = StaticText("")

        self.playlists_all = bmx.getPlaylistJson()

        self.onLayoutFinish.append(self.__layoutFinished)

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.keyCancel,
            "green": self.deleteBouquets,
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

    def buildListEntry(self, name, index, selected):
        if selected:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_on.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "lock_off.png"))
        return (pixmap, str(name), index, selected)

    def getStartList(self):
        for playlist in self.playlists_all:
            if playlist["playlist_info"]["bouquet"] is True:
                self.start_list.append([str(playlist["playlist_info"]["name"]), playlist["playlist_info"]["index"], False])

        self.draw_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.start_list]
        self["list"].setList(self.draw_list)

    def refresh(self):
        self.draw_list = []
        self.draw_list = [self.buildListEntry(x[0], x[1], x[2]) for x in self.start_list]
        self["list"].updateList(self.draw_list)

    def toggleSelection(self):
        if len(self["list"].list) > 0:
            idx = self["list"].getIndex()
            self.start_list[idx][2] = not self.start_list[idx][2]
            self.refresh()

    def toggleAllSelection(self):
        for idx in range(len(self["list"].list)):
            self.start_list[idx][2] = not self.start_list[idx][2]
        self.refresh()

    def getSelectionsList(self):
        return [item[0] for item in self.start_list if item[2]]

    def clearAllSelection(self):
        for idx in range(len(self["list"].list)):
            self.start_list[idx][2] = False
        self.refresh()

    def keyCancel(self):
        self.close()

    def deleteBouquets(self):
        selected_bouquet_list = self.getSelectionsList()

        for bouquet_name in selected_bouquet_list:
            safe_name = bmx.safeName(bouquet_name)

            with open("/etc/enigma2/bouquets.tv", "r+") as f:
                lines = f.readlines()
                f.seek(0)
                f.truncate()

                for line in lines:
                    if "bouquetmakerxtream_live_" + str(safe_name) + "_" in line:
                        continue
                    if "bouquetmakerxtream_vod_" + str(safe_name) + "_" in line:
                        continue
                    if "bouquetmakerxtream_series_" + str(safe_name) + "_" in line:
                        continue
                    if "bouquetmakerxtream_" + str(safe_name) + ".tv" in line:
                        continue
                    f.write(line)

            bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(safe_name) + "_")
            bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(safe_name) + "_")
            bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(safe_name) + "_")
            bmx.purge("/etc/enigma2", "bouquetmakerxtream_" + str(safe_name))

            if epgimporter is True:
                bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(safe_name) + ".channels.xml")

                # remove sources from source file
                source_file = "/etc/epgimport/bouquetmakerxtream.sources.xml"

                if os.path.isfile(source_file):
                    try:
                        import xml.etree.ElementTree as ET

                        tree = ET.parse(source_file, parser=ET.XMLParser(encoding="utf-8"))
                        root = tree.getroot()

                        for elem in root.iter():
                            for child in list(elem):
                                if child.tag == "source":

                                    description = child.find("description").text if child.find("description") is not None else ""
                                    if safe_name in description:
                                        elem.remove(child)

                        tree.write(source_file)
                    except Exception as e:
                        print(e)

            self.deleteBouquetFile(bouquet_name)
            glob.firstrun = True
            glob.current_selection = 0
            glob.current_playlist = []
            bmx.refreshBouquets()
        self.close()

    def deleteBouquetFile(self, bouquet_name):
        for playlist in self.playlists_all:
            if playlist["playlist_info"]["name"] == bouquet_name:
                playlist["playlist_info"]["bouquet"] = False

        # delete leftover empty dicts
        self.playlists_all = [_f for _f in self.playlists_all if _f]

        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
