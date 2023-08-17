#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import processfiles as pfiles
from .plugin import skin_directory, common_path, version, pythonFull, cfg
from .bouquetStaticText import StaticText

from Components.ActionMap import ActionMap
from Components.Sources.List import List

from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

import os


class BouquetMakerXtream_MainMenu(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())

        skin = os.path.join(skin_path, "mainmenu.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.list = []
        self.drawList = []
        self.playlists_all = []
        self["list"] = List(self.drawList, enableWrapAround=True)

        self.setup_title = (_("Main Menu"))
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["version"] = StaticText()

        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
            "red": self.quit,
            "green": self.__next__,
            "ok": self.__next__,
            "cancel": self.quit,
            "menu": self.settings,
        }, -2)

        self["version"].setText(version)

        self.onFirstExecBegin.append(self.check_dependencies)
        self.onLayoutFinish.append(self.__layoutFinished)

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def check_dependencies(self):

        try:
            if cfg.locationvalid.getValue() is False:
                self.session.open(MessageBox, _("Playlists.txt location is invalid and has been reset."), type=MessageBox.TYPE_INFO, timeout=5)
                cfg.locationvalid.setValue(True)
                cfg.save()
        except:
            pass

        dependencies = True

        try:
            import requests

            if pythonFull < 3.9:
                print("*** checking multiprocessing ***")
                from multiprocessing.pool import ThreadPool
        except Exception as e:
            print("**** missing dependencies ***")
            print(e)
            dependencies = False

        try:
            import lzma
        except Exception as e:
            print(e)
            try:
                from backports import lzma
            except Exception as e:
                print(e)
                dependencies = False

        if dependencies is False:
            os.chmod("/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/dependencies.sh", 0o0755)
            cmd1 = ". /usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/dependencies.sh"
            self.session.openWithCallback(self.start, Console, title="Checking Python Dependencies", cmdlist=[cmd1], closeOnSuccess=False)
        else:
            self.start()

    def start(self, answer=None):
        # print("*** mainmenu-processfiles start ***")
        self.playlists_all = pfiles.processfiles()
        # print("*** mainmenu-processfiles finished ***")
        self.createSetup()

    def createSetup(self):
        self.list = []

        if self.playlists_all:
            self.list.append([1, _("Playlists")])

        self.list.append([2, _("Add Playlist")])
        self.list.append([3, _("Main Settings")])

        self.bouquets_exist = False

        for playlist in self.playlists_all:
            if playlist["playlist_info"]["bouquet"] is True:
                self.bouquets_exist = True
                break

        if self.bouquets_exist:
            self.list.append([4, _("Update Bouquets")])
            self.list.append([5, _("Delete Bouquets")])

        self.list.append([6, _("About")])

        self.drawList = []
        self.drawList = [buildListEntry(x[0], x[1]) for x in self.list]
        self["list"].setList(self.drawList)

    def playlists(self):
        from . import playlists
        self.session.openWithCallback(self.start, playlists.BouquetMakerXtream_Playlists)

    def settings(self):
        from . import settings
        self.session.openWithCallback(self.start, settings.BouquetMakerXtream_Settings)

    def addServer(self):
        from . import server
        self.session.openWithCallback(self.start, server.BouquetMakerXtream_AddServer)

    def about(self):
        from . import about
        self.session.openWithCallback(self.start, about.BouquetMakerXtream_About)

    def deleteSet(self):
        from . import deletebouquets
        self.session.openWithCallback(self.start, deletebouquets.BouquetMakerXtream_DeleteBouquets)

    def update(self):
        return
        from . import update
        self.session.openWithCallback(self.createSetup, update.BouquetMakerXtream_Update, "manual")
        self.close()

    def __next__(self):
        index = self["list"].getCurrent()[0]

        if self["list"].getCurrent():
            if index == 1:
                self.playlists()
            if index == 2:
                self.addServer()
            if index == 3:
                self.settings()
            if index == 4:
                self.update()
            if index == 5:
                self.deleteSet()
            if index == 6:
                self.about()

    def quit(self):
        glob.firstrun = 0
        self.close(False)


def buildListEntry(index, title):
    png = None

    if index == 1:
        png = LoadPixmap(common_path + "playlists.png")
    if index == 3:
        png = LoadPixmap(common_path + "settings.png")
    if index == 2:
        png = LoadPixmap(common_path + "addplaylist.png")
    if index == 4:
        png = LoadPixmap(common_path + "updateplaylists.png")
    if index == 5:
        png = LoadPixmap(common_path + "deleteplaylist.png")
    if index == 6:
        png = LoadPixmap(common_path + "about.png")

    return (index, str(title), png)
