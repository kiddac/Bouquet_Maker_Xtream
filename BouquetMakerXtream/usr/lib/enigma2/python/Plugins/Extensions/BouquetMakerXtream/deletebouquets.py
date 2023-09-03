#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import globalfunctions as bmx
from . import bouquet_globals as glob

from .plugin import skin_path, common_path, playlists_json, epgimporter, version
from .bouquetStaticText import StaticText

from Components.ActionMap import ActionMap
from Components.Sources.List import List

from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import json
import os


class BouquetMakerXtream_DeleteBouquets(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        skin = os.path.join(skin_path, "bouquets.xml")
        with open(skin, "r") as f:
            self.skin = f.read()
        self.setup_title = _("Delete Bouquets")

        # new list code
        self.startList = []
        self.drawList = []
        self["list"] = List(self.drawList)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Delete"))
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Clear All"))
        self["key_info"] = StaticText("")
        self["version"] = StaticText()

        self.playlists_all = bmx.getPlaylistJson()

        self.onLayoutFinish.append(self.__layoutFinished)

        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
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
                self.startList.append([str(playlist["playlist_info"]["name"]), playlist["playlist_info"]["index"], False])

        self.drawList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.startList]
        self["list"].setList(self.drawList)

    def refresh(self):
        self.drawList = []
        self.drawList = [self.buildListEntry(x[0], x[1], x[2]) for x in self.startList]
        self["list"].updateList(self.drawList)

    def toggleSelection(self):
        if len(self["list"].list) > 0:
            idx = self["list"].getIndex()
            self.startList[idx][2] = not self.startList[idx][2]
            self.refresh()

    def toggleAllSelection(self):
        for idx, item in enumerate(self["list"].list):
            self.startList[idx][2] = not self.startList[idx][2]
        self.refresh()

    def getSelectionsList(self):
        return [item[0] for item in self.startList if item[2]]

    def clearAllSelection(self):
        for idx, item in enumerate(self["list"].list):
            self.startList[idx][2] = False
        self.refresh()

    def keyCancel(self):
        self.close()

    def deleteBouquets(self):
        selectedBouquetList = self.getSelectionsList()

        for x in selectedBouquetList:
            bouquet_name = x
            safeName = bmx.safeName(bouquet_name)

            with open("/etc/enigma2/bouquets.tv", "r+") as f:
                lines = f.readlines()
                f.seek(0)
                f.truncate()

                for line in lines:
                    if "bouquetmakerxtream_live_" + str(safeName) + "_" in line:
                        continue
                    if "bouquetmakerxtream_vod_" + str(safeName) + "_" in line:
                        continue
                    if "bouquetmakerxtream_series_" + str(safeName) + "_" in line:
                        continue
                    if "bouquetmakerxtream_" + str(safeName) + ".tv" in line:
                        continue
                    f.write(line)

            bmx.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(safeName) + "_")
            bmx.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(safeName) + "_")
            bmx.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(safeName) + "_")
            bmx.purge("/etc/enigma2", str(safeName) + str(".tv"))

            if epgimporter is True:
                bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(safeName) + ".channels.xml")

                # remove sources from source file
                sourcefile = "/etc/epgimport/bouquetmakerxtream.sources.xml"

                if os.path.isfile(sourcefile):

                    import xml.etree.ElementTree as ET
                    tree = ET.parse(sourcefile)
                    root = tree.getroot()

                    for elem in root.iter():
                        for child in list(elem):
                            description = ""
                            if child.tag == "source":
                                try:
                                    description = child.find("description").text
                                    if safeName in description:
                                        elem.remove(child)
                                except:
                                    pass

                    tree.write(sourcefile)

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
