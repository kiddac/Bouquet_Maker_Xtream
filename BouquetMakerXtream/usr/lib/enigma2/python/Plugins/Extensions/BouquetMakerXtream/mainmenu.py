#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from . import processfiles as pfiles
from .bmxStaticText import StaticText
from .plugin import cfg, COMMON_PATH, PLAYLISTS_JSON, PYTHON_FULL, SKIN_DIRECTORY, VERSION, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


class BmxMainMenu(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        glob.FINISHED = False

        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())

        skin = os.path.join(skin_path, "mainmenu.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()

        self.list = []
        self.draw_list = []
        self.playlists_all = []
        self["list"] = List(self.draw_list, enableWrapAround=True)

        self.setup_title = _("Main Menu")
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["version"] = StaticText()

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.quit,
            "green": self.__next__,
            "ok": self.__next__,
            "cancel": self.quit,
            "menu": self.settings,
        }, -2)

        self["version"].setText(VERSION)

        self.onFirstExecBegin.append(self.check_dependencies)
        self.onLayoutFinish.append(self.__layout_finished)

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def check_dependencies(self):
        try:
            if cfg.location_valid.getValue() is False:
                self.session.open(MessageBox, _("Playlists.txt location is invalid and has been reset."), type=MessageBox.TYPE_INFO, timeout=5)
                cfg.location_valid.setValue(True)
                cfg.save()
        except Exception:
            pass

        dependencies = True

        try:
            import requests

            if PYTHON_FULL < 3.9:
                from multiprocessing.pool import ThreadPool
        except ImportError as e:
            print(e)
            dependencies = False

        """
        try:
            import lzma
        except ImportError as e:
            print(e)
            try:
                from backports import lzma
            except ImportError as ex:
                print(ex)
                dependencies = False
                """

        if dependencies is False:
            os.chmod("/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/dependencies.sh", 0o0755)
            cmd1 = ". /usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/dependencies.sh"
            self.session.openWithCallback(self.start, Console, title="Checking Python Dependencies", cmdlist=[cmd1], closeOnSuccess=False)
        else:
            self.start()

    def start(self, answer=None):
        if glob.FINISHED and cfg.auto_close.getValue() is True:
            self.close()

        self.playlists_all = pfiles.processfiles()

        # clear stream data if populated after a crash
        if self.playlists_all:
            for playlist in self.playlists_all:
                playlist["data"]["live_streams"] = []
                playlist["data"]["vod_streams"] = []
                playlist["data"]["series_streams"] = []

        self.create_setup()

    def create_setup(self):
        self.list = []

        if self.playlists_all:
            self.list.append([1, _("Playlists")])

        self.list.append([3, _("Main Settings")])

        self.bouquets_exist = False

        for playlist in self.playlists_all:
            if playlist["playlist_info"]["bouquet"] is True:
                self.bouquets_exist = True
                break

        if self.bouquets_exist:
            self.list.append([4, _("Update Bouquets")])
            self.list.append([5, _("Delete Bouquets")])
            self.list.append([6, _("Delete All BMX Bouquets")])

        self.list.append([2, _("Add Playlist")])
        self.list.append([7, _("About")])

        self.draw_list = []
        self.draw_list = [build_list_entry(x[0], x[1]) for x in self.list]
        self["list"].setList(self.draw_list)

    def playlists(self):
        from . import playlists

        self.session.openWithCallback(self.start, playlists.BmxPlaylists)

    def settings(self):
        from . import settings

        self.session.openWithCallback(self.start, settings.BmxSettings)

    def add_server(self):
        from . import server

        self.session.openWithCallback(self.start, server.BmxAddServer)

    def about(self):
        from . import about

        self.session.openWithCallback(self.start, about.BmxAbout)

    def delete_set(self):
        from . import deletebouquets

        self.session.openWithCallback(self.start, deletebouquets.BmxDeleteBouquets)

    def delete_all(self, answer=None):
        if answer is None:
            self.session.openWithCallback(self.delete_all, MessageBox, _("Delete all BMX created bouquets?"))
        elif answer:
            bmx.purge("/etc/enigma2", "bouquetmakerxtream")

            with open("/etc/enigma2/bouquets.tv", "r+", encoding="utf-8") as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if "bouquetmakerxtream" not in line:
                        f.write(line)
                f.truncate()

            bmx.purge("/etc/epgimport", "bouquetmakerxtream")

            self.playlists_all = bmx.get_playlist_json()

            for playlist in self.playlists_all:
                playlist["playlist_info"]["bouquet"] = False

            # delete leftover empty dicts
            self.playlists_all = [_f for _f in self.playlists_all if _f]

            with open(PLAYLISTS_JSON, "w", encoding="utf-8") as f:
                json.dump(self.playlists_all, f)

            bmx.refresh_bouquets()
            self.create_setup()
        return

    def update(self):
        # return
        from . import update

        self.session.openWithCallback(self.create_setup, update.BmxUpdate, "manual")

    def __next__(self):
        if self["list"].getCurrent():
            index = self["list"].getCurrent()[0]

            if index == 1:
                self.playlists()
            if index == 2:
                self.add_server()
            if index == 3:
                self.settings()
            if index == 4:
                self.update()
            if index == 5:
                self.delete_set()
            if index == 6:
                self.delete_all()
            if index == 7:
                self.about()

    def quit(self):
        glob.FIRSTRUN = 0
        self.close()


def build_list_entry(index, title):
    png = None

    if index == 1:
        png = LoadPixmap(COMMON_PATH + "playlists.png")
    if index == 3:
        png = LoadPixmap(COMMON_PATH + "settings.png")
    if index == 2:
        png = LoadPixmap(COMMON_PATH + "addplaylist.png")
    if index == 4:
        png = LoadPixmap(COMMON_PATH + "updateplaylists.png")
    if index == 5:
        png = LoadPixmap(COMMON_PATH + "deleteplaylist.png")
    if index == 6:
        png = LoadPixmap(COMMON_PATH + "deleteplaylist.png")
    if index == 7:
        png = LoadPixmap(COMMON_PATH + "about.png")

    return (index, str(title), png)
