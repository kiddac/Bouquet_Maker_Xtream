#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Screen import Screen

from . import _
from . import bouquet_globals as glob
from .bmxStaticText import StaticText
from .plugin import cfg, SKIN_DIRECTORY, PYTHON_VER

if PYTHON_VER == 2:
    from io import open


class BmxUserInfo(Screen):
    ALLOW_SUSPEND = True

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "userinfo.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()

        self.setup_title = _("User Information")

        self["status"] = Label("")
        self["expiry"] = Label("")
        self["created"] = Label("")
        self["trial"] = Label("")
        self["activeconn"] = Label("")
        self["maxconn"] = Label("")
        self["formats"] = Label("")
        self["realurl"] = Label("")
        self["timezone"] = Label("")
        self["server_offset"] = Label("")

        # fake labels for skin text translations
        t_status = _("Status:")
        t_istrial = _("Is Trial:")
        t_activeconnections = _("Active Connections:")
        t_maxconnections = _("Max Connections:")
        t_createdat = _("Created At:")
        t_expirydate = _("Expiry Date:")
        t_allowedformats = _("Allowed Output Formats:")
        t_realurl = _("Real URL:")
        t_timezone = _("Timezone:")
        t_server_offset = _("Server Offset:")

        self["actions"] = ActionMap(["BMXActions"], {
            "ok": self.quit,
            "cancel": self.quit,
            "red": self.quit,
        }, -2)

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))

        self.onFirstExecBegin.append(self.create_user_setup)
        self.onLayoutFinish.append(self.__layout_finished)

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def create_user_setup(self):
        if "status" in glob.CURRENT_PLAYLIST["user_info"]:
            self["status"].setText(str(glob.CURRENT_PLAYLIST["user_info"]["status"]))

        if "exp_date" in glob.CURRENT_PLAYLIST["user_info"]:
            try:
                self["expiry"].setText(str(datetime.fromtimestamp(int(glob.CURRENT_PLAYLIST["user_info"]["exp_date"])).strftime("%d-%m-%Y  %H:%M")))
            except Exception:
                self["expiry"].setText("Null")

        if "created_at" in glob.CURRENT_PLAYLIST["user_info"]:
            try:
                self["created"].setText(str(datetime.fromtimestamp(int(glob.CURRENT_PLAYLIST["user_info"]["created_at"])).strftime("%d-%m-%Y  %H:%M")))
            except Exception:
                self["created"].setText("Null")

        if "is_trial" in glob.CURRENT_PLAYLIST["user_info"]:
            self["trial"].setText(str(glob.CURRENT_PLAYLIST["user_info"]["is_trial"]))

        if "active_cons" in glob.CURRENT_PLAYLIST["user_info"]:
            self["activeconn"].setText(str(glob.CURRENT_PLAYLIST["user_info"]["active_cons"]))

        if "max_connections" in glob.CURRENT_PLAYLIST["user_info"]:
            self["maxconn"].setText(str(glob.CURRENT_PLAYLIST["user_info"]["max_connections"]))

        if "allowed_output_formats" in glob.CURRENT_PLAYLIST["user_info"]:
            self["formats"].setText(str(json.dumps(glob.CURRENT_PLAYLIST["user_info"]["allowed_output_formats"])).lstrip("[").rstrip("]"))

        if "url" in glob.CURRENT_PLAYLIST["server_info"]:
            self["realurl"].setText(str(glob.CURRENT_PLAYLIST["server_info"]["url"]))

        if "timezone" in glob.CURRENT_PLAYLIST["server_info"]:
            self["timezone"].setText(str(glob.CURRENT_PLAYLIST["server_info"]["timezone"]))

        if "server_offset" in glob.CURRENT_PLAYLIST["data"]:
            self["server_offset"].setText(str(glob.CURRENT_PLAYLIST["data"]["server_offset"]))

    def quit(self):
        self.close()
