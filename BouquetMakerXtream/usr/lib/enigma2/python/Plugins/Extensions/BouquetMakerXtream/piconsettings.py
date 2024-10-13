#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import picons
from .bmxStaticText import StaticText
from .plugin import cfg, skin_directory

from Components.ActionMap import ActionMap
from Components.config import ConfigSelection, ConfigText, config, configfile, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from enigma import ePoint
from Screens import Standby
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

import os


class BmxPiconSettings(ConfigListScreen, Screen):
    ALLOW_SUSPEND = True

    def __init__(self, session):
        Screen.__init__(self, session)

        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "settings.xml")
        if os.path.exists("/var/lib/dpkg/status"):
            skin = os.path.join(skin_path, "DreamOS/settings.xml")

        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Picon Settings")

        self.onChangedEntry = []

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["information"] = StaticText("")

        self["VKeyIcon"] = Pixmap()
        self["VKeyIcon"].hide()
        self["HelpWindow"] = Pixmap()
        self["HelpWindow"].hide()

        self["actions"] = ActionMap(["BMXActions"], {
            "cancel": self.cancel,
            "red": self.cancel,
            "green": self.save,
            "ok": self.ok,
        }, -2)

        self.initConfig()
        self.onLayoutFinish.append(self.__layoutFinished)

    def clearCaches(self):
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def cancel(self, answer=None):
        if answer is None:
            if self["config"].isChanged():
                self.session.openWithCallback(self.cancel, MessageBox, _("Really close without saving settings?"))
            else:
                self.close()
        elif answer:
            for x in self["config"].list:
                x[1].cancel()

            self.close()
        return

    def save(self):
        if self["config"].isChanged():
            for x in self["config"].list:
                x[1].save()
            cfg.save()
            configfile.save()

        self.clearCaches()

        """
        if cfg.picon_location.value == "custom":
            cfg.picon_location.setValue(cfg.picon_custom.value)
            """

        self.session.openWithCallback(self.close, picons.BmxDownloadPicons)
        # self.close()

    def changedFinished(self):
        self.session.openWithCallback(self.executeRestart, MessageBox, _("You need to restart the GUI") + "\n" + _("Do you want to restart now?"), MessageBox.TYPE_YESNO)
        self.close()

    def executeRestart(self, result):
        if result:
            Standby.quitMainloop(3)
        else:
            self.close()

    def initConfig(self):

        self.cfg_picon_location = getConfigListEntry(_("Picon download location"), cfg.picon_location)
        self.cfg_picon_size = getConfigListEntry(_("Picon size"), cfg.picon_size)
        self.cfg_picon_type = getConfigListEntry(_("Picon type"), cfg.picon_type)
        # self.cfg_picon_bitdepth = getConfigListEntry(_("Picon bit depth. 8bit is 256 colours max."), cfg.picon_bitdepth)
        self.cfg_picon_overwrite = getConfigListEntry(_("Overwrite picons with the same name"), cfg.picon_overwrite)
        self.cfg_picon_custom = getConfigListEntry(_("Custom location. Manual symlink required"), cfg.picon_custom)
        self.cfg_max_threads = getConfigListEntry(_("Max download threads. Increase for speed. Reduce if downloads are freezing"), cfg.max_threads)
        self.cfg_picon_max_size = getConfigListEntry(_("Max size of source picon"), cfg.picon_max_size)
        self.cfg_picon_max_width = getConfigListEntry(_("Max width of source picon"), cfg.picon_max_width)

        self.createSetup()

    def createSetup(self):
        self.list = []
        self.list.append(self.cfg_picon_location)
        if cfg.picon_location.value == "custom":
            self.list.append(self.cfg_picon_custom)

        self.list.append(self.cfg_picon_size)
        self.list.append(self.cfg_picon_type)
        # self.list.append(self.cfg_picon_bitdepth)
        self.list.append(self.cfg_picon_overwrite)
        self.list.append(self.cfg_max_threads)
        self.list.append(self.cfg_picon_max_size)
        self.list.append(self.cfg_picon_max_width)

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        self.handleInputHelpers()

    def handleInputHelpers(self):
        currConfig = self["config"].getCurrent()

        if currConfig is not None:
            if isinstance(currConfig[1], ConfigText):
                if "VKeyIcon" in self:
                    try:
                        self["VirtualKB"].setEnabled(True)
                    except:
                        pass

                    try:
                        self["virtualKeyBoardActions"].setEnabled(True)
                    except:
                        pass
                    self["VKeyIcon"].show()

                if "HelpWindow" in self and currConfig[1].help_window and currConfig[1].help_window.instance is not None:
                    helpwindowpos = self["HelpWindow"].getPosition()
                    currConfig[1].help_window.instance.move(ePoint(helpwindowpos[0], helpwindowpos[1]))

            else:
                if "VKeyIcon" in self:
                    try:
                        self["VirtualKB"].setEnabled(False)
                    except:
                        pass

                    try:
                        self["virtualKeyBoardActions"].setEnabled(False)
                    except:
                        pass
                    self["VKeyIcon"].hide()

    def changedEntry(self):
        self.item = self["config"].getCurrent()
        for x in self.onChangedEntry:
            x()

        try:
            if isinstance(self["config"].getCurrent()[1], ConfigSelection):
                self.createSetup()
        except:
            pass

    def getCurrentEntry(self):
        return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

    def getCurrentValue(self):
        return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

    def ok(self):
        sel = self["config"].getCurrent()[1]
        if sel and sel == cfg.picon_custom:
            self.openDirectoryBrowser(cfg.picon_custom.value, "location")

    def openDirectoryBrowser(self, path, cfgitem):
        if cfgitem == "location":
            try:
                self.session.openWithCallback(
                    self.openDirectoryBrowserCB,
                    LocationBox,
                    windowTitle=_("Choose Directory:"),
                    text=_("Choose directory"),
                    currDir=str(path),
                    bookmarks=config.movielist.videodirs,
                    autoAdd=True,
                    editDir=True,
                    inhibitDirs=["/bin", "/boot", "/dev", "/home", "/lib", "/proc", "/run", "/sbin", "/sys", "/usr", "/var"])
            except Exception as e:
                print(e)

    def openDirectoryBrowserCB(self, path):
        if path is not None:
            cfg.picon_custom.setValue(path)
        return
