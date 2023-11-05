#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

import requests
from Components.ActionMap import ActionMap
from Components.config import ConfigEnableDisable, ConfigNumber, ConfigSelection, ConfigText, ConfigYesNo, NoSave, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from enigma import ePoint
from requests.adapters import HTTPAdapter
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . import _
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import hdr, playlist_file, skin_directory, cfg

try:
    from http.client import HTTPConnection

    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection

    HTTPConnection.debuglevel = 0


class BmxAddServer(ConfigListScreen, Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "settings.xml")

        if os.path.exists("/var/lib/dpkg/status"):
            skin = os.path.join(skin_path, "DreamOS/settings.xml")

        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Add Playlist")

        self.onChangedEntry = []

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Save"))
        self["information"] = StaticText(_("You can manually add playlist urls to /etc/enigma2/bouquetmakerxtream/playlists.txt file"))

        self["VKeyIcon"] = Pixmap()
        self["VKeyIcon"].hide()
        self["HelpWindow"] = Pixmap()
        self["HelpWindow"].hide()

        self.address = ""
        self.protocol = "http://"
        self.output = "ts"

        self["actions"] = ActionMap(["BMXActions"], {
            "cancel": self.cancel,
            "red": self.cancel,
            "green": self.save,
            "ok": self.void,
        }, -2)

        self.playlists_all = bmx.getPlaylistJson()

        self.onFirstExecBegin.append(self.initConfig)
        self.onLayoutFinish.append(self.__layoutFinished)

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

    def void(self):
        curr_config = self["config"].getCurrent()
        if isinstance(curr_config[1], ConfigNumber):
            pass

    def initConfig(self):
        self.playlist_type_cfg = NoSave(ConfigSelection(default="standard", choices=[("standard", _("Xtream codes / XUI ONE (get.php)")), ("external", _("External #EXTM3U playlist"))]))
        self.name_cfg = NoSave(ConfigText(default="IPTV", fixed_size=False))
        self.protocol_cfg = NoSave(ConfigSelection(default=self.protocol, choices=[("http://", "http://"), ("https://", "https://")]))
        self.server_cfg = NoSave(ConfigText(fixed_size=False))
        self.port_cfg = NoSave(ConfigText(fixed_size=False))
        self.username_cfg = NoSave(ConfigText(fixed_size=False))
        self.password_cfg = NoSave(ConfigText(fixed_size=False))
        self.output_cfg = NoSave(ConfigSelection(default=self.output, choices=[("ts", "ts"), ("m3u8", "m3u8")]))
        self.url_cfg = NoSave(ConfigText(default=self.address, fixed_size=False))
        self.createSetup()

    def createSetup(self):
        self.list = []

        self.list.append(getConfigListEntry(_("Select playlist type:"), self.playlist_type_cfg))
        if self.playlist_type_cfg.value == "standard":
            self.list.append(getConfigListEntry(_("Short name or provider name:"), self.name_cfg))
            self.list.append(getConfigListEntry(_("Protocol:"), self.protocol_cfg))
            self.list.append(getConfigListEntry(_("Server URL: i.e. domain.xyz"), self.server_cfg))
            self.list.append(getConfigListEntry(_("Port: (optional) i.e. 8080"), self.port_cfg))
            self.list.append(getConfigListEntry(_("Username:"), self.username_cfg))
            self.list.append(getConfigListEntry(_("Password:"), self.password_cfg))
            self.list.append(getConfigListEntry(_("Output:"), self.output_cfg))
        else:
            self.list.append(getConfigListEntry(_("Short name or provider name:"), self.name_cfg))
            self.list.append(getConfigListEntry(_("Protocol:"), self.protocol_cfg))
            self.list.append(getConfigListEntry(_("External url: i.e pastebin.com/raw/blahblah"), self.url_cfg))

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        self.handleInputHelpers()

    def handleInputHelpers(self):
        currConfig = self["config"].getCurrent()

        if currConfig is not None:
            if isinstance(currConfig[1], ConfigText):
                if "VKeyIcon" in self:
                    if isinstance(currConfig[1], ConfigNumber):
                        try:
                            self["VirtualKB"].setEnabled(False)
                        except:
                            pass

                        try:
                            self["virtualKeyBoardActions"].setEnabled(False)
                        except:
                            pass

                        self["VKeyIcon"].hide()
                    else:
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
                    self["VKeyIcon"].hide()

    def save(self):
        if self["config"].isChanged():
            if self.playlist_type_cfg.value == "standard":
                name = self.name_cfg.value.strip()
                protocol = self.protocol_cfg.value
                domain = self.server_cfg.value.strip().lower()
                port = self.port_cfg.value

                if port:
                    host = "%s%s:%s" % (protocol, domain, port)
                else:
                    host = "%s%s" % (protocol, domain)

                username = self.username_cfg.value.strip()
                password = self.password_cfg.value.strip()
                list_type = "m3u"
                output = self.output_cfg.value

                playlist_line = "%s/get.php?username=%s&password=%s&type=%s&output=%s #%s" % (host, username, password, list_type, output, name)
                api_line = "%s/player_api.php?username=%s&password=%s" % (host, username, password)

                valid = self.checkLine(api_line)
            else:
                name = self.name_cfg.value.strip()
                protocol = self.protocol_cfg.value
                url = self.url_cfg.value.strip()
                host = "%s%s" % (protocol, url)

                playlist_line = "%s #%s" % (host, name)

                valid = self.checkLine(host)

            # check url has response
            if not valid:
                self.session.open(MessageBox, _("Details are not valid or unauthorised"), type=MessageBox.TYPE_INFO, timeout=5)
                return

            # check name is not blank
            if name is None or len(name) < 3:
                self.session.open(MessageBox, _("Bouquet name cannot be blank. Please enter a unique bouquet name. Minimum 2 characters."), MessageBox.TYPE_ERROR, timeout=10)
                self.createSetup()
                return

            # check name exists
            if self.playlists_all:
                for playlists in self.playlists_all:
                    if playlists["playlist_info"]["name"] == name:
                        self.session.open(MessageBox, _("Name already used. Please enter a unique name."), MessageBox.TYPE_ERROR, timeout=10)
                        return

            # check playlists.txt file hasn't been deleted
            if not os.path.isfile(playlist_file):
                with open(playlist_file, "a") as f:
                    f.close()

            # update playlists.txt file
            with open(playlist_file, "a") as f:
                f.write("\n" + str(playlist_line) + "\n")
            self.session.open(MessageBox, _("Playlist added successfully."), type=MessageBox.TYPE_INFO, timeout=5)
            self.close()

    def changedEntry(self):
        self.item = self["config"].getCurrent()
        for x in self.onChangedEntry:
            x()

        try:
            if isinstance(self["config"].getCurrent()[1], ConfigEnableDisable) or isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
                self.createSetup()
        except:
            pass

    def checkLine(self, url):
        valid = False
        r = ""
        adapter = HTTPAdapter(max_retries=0)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""
        try:
            with http.get(url, headers=hdr, timeout=10, verify=False, stream=True) as r:
                r.raise_for_status()
                if r.status_code == requests.codes.ok:
                    try:
                        if self.playlist_type_cfg.value == "standard":
                            response = r.json()
                            if "user_info" in response and "auth" in response["user_info"] and response["user_info"]["auth"] == 1:
                                valid = True
                        else:
                            valid = True
                    except Exception as e:
                        print(e)

        except Exception as e:
            print(("Error Connecting: %s" % e))

        return valid
