#!/usr/bin/python
# -*- coding: utf-8 -*-


import os

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Screen import Screen

from . import _
from .bmxStaticText import StaticText
from .plugin import cfg, SKIN_DIRECTORY, VERSION, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


class BmxAbout(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "about.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()

        self.setup_title = (_("About"))

        self["actions"] = ActionMap(["BMXActions"], {
            "ok": self.quit,
            "green": self.quit,
            "red": self.quit,
            "cancel": self.quit,
        }, -2)
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["version"] = StaticText("")
        self["about"] = Label("")
        self.onFirstExecBegin.append(self.create_setup)
        self.onLayoutFinish.append(self.__layout_finished)

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def create_setup(self):
        self.credit = "BouquetMakerXtream " + str(VERSION) + " - KiddaC\n\n"
        self.credit += (_("Support for this plugin and latest versions can be found on https://linuxsat-support.com\n\n"))
        self.credit += (_("Plugin enables the simple bouquet creation of standard Xtream codes/XUI One, external and local m3u8 playlists. \nPlay your files via your TV bouquets.\n\n"))
        self.credit += (_("Credits:\n"))
        self.credit += (_("AutoBouquetsMaker, EpgImporter, AutoBackup (used as code reference).\n"))
        self.credit += (_("And thanks to all the other coders and Linuxsat testers who helped in the development of this project.\n\n"))
        self.credit += (_("If you would like to buy me a beer or a coffee: https://paypal.me/kiddac or https://ko-fi.com/kiddac\n"))
        self.credit += (_("Cheers - all donations are very much appreciated."))
        self["about"].setText(self.credit)

    def quit(self):
        self.close()
