#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, COMMON_PATH, EPGIMPORTER, PLAYLISTS_JSON, SKIN_DIRECTORY, VERSION, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


class BmxDeleteBouquets(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "bouquets.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()
        self.setup_title = _("Delete Bouquets")

        # new list code
        self.start_list = []
        self.draw_list = []
        self["list"] = List(self.draw_list)

        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Delete"))
        self["key_yellow"] = StaticText(_("Invert"))
        self["key_blue"] = StaticText(_("Clear All"))
        self["key_info"] = StaticText("")
        self["version"] = StaticText("")

        self.playlists_all = bmx.get_playlist_json()

        self.onLayoutFinish.append(self.__layout_finished)

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.key_cancel,
            "green": self.delete_bouquets,
            "yellow": self.toggle_all_selection,
            "blue": self.clear_all_selection,
            "cancel": self.key_cancel,
            "ok": self.toggle_selection,
        }, -2)

        self["version"].setText(VERSION)

        self.get_start_list()
        self.refresh()

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def build_list_entry(self, name, index, selected):
        if selected:
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "lock_on.png"))
        else:
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "lock_off.png"))
        return (pixmap, str(name), index, selected)

    def get_start_list(self):
        for playlist in self.playlists_all:
            if playlist["playlist_info"]["bouquet"] is True:
                self.start_list.append([str(playlist["playlist_info"]["name"]), playlist["playlist_info"]["index"], False])

        self.draw_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.start_list]
        self["list"].setList(self.draw_list)

    def refresh(self):
        self.draw_list = []
        self.draw_list = [self.build_list_entry(x[0], x[1], x[2]) for x in self.start_list]
        self["list"].updateList(self.draw_list)

    def toggle_selection(self):
        if len(self["list"].list) > 0:
            idx = self["list"].getIndex()
            self.start_list[idx][2] = not self.start_list[idx][2]
            self.refresh()

    def toggle_all_selection(self):
        for idx, item in enumerate(self["list"].list):
            self.start_list[idx][2] = not self.start_list[idx][2]
        self.refresh()

    def get_selections_list(self):
        return [item[0] for item in self.start_list if item[2]]

    def clear_all_selection(self):
        for idx, item in enumerate(self["list"].list):
            self.start_list[idx][2] = False
        self.refresh()

    def key_cancel(self):
        self.close()

    def delete_bouquets(self):
        selected_bouquet_list = self.get_selections_list()

        for x in selected_bouquet_list:
            bouquet_name = x
            safe_name = bmx.safe_name(bouquet_name)

            with open("/etc/enigma2/bouquets.tv", "r+", encoding="utf-8") as f:
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
            bmx.purge("/etc/enigma2", str(safe_name) + str(".tv"))

            if EPGIMPORTER is True:
                bmx.purge("/etc/epgimport", "bouquetmakerxtream." + str(safe_name) + ".channels.xml")

                # remove sources from source file
                source_file = "/etc/epgimport/bouquetmakerxtream.sources.xml"

                if os.path.isfile(source_file):
                    import xml.etree.ElementTree as ET

                    tree = ET.parse(source_file)
                    root = tree.getroot()

                    for elem in root.iter():
                        for child in list(elem):
                            description = ""
                            if child.tag == "source":
                                try:
                                    description = child.find("description").text
                                    if safe_name in description:
                                        elem.remove(child)
                                except:
                                    pass

                    tree.write(source_file)

            self.delete_bouquet_file(bouquet_name)
            glob.FIRSTRUN = True
            glob.CURRENT_SELECTION = 0
            glob.CURRENT_PLAYLIST = []
            bmx.refresh_bouquets()
        self.close()

    def delete_bouquet_file(self, bouquet_name):
        for playlist in self.playlists_all:
            if playlist["playlist_info"]["name"] == bouquet_name:
                playlist["playlist_info"]["bouquet"] = False

        # delete leftover empty dicts
        self.playlists_all = [_f for _f in self.playlists_all if _f]

        with open(PLAYLISTS_JSON, "w", encoding="utf-8") as f:
            json.dump(self.playlists_all, f)
