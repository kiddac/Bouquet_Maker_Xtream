#!/usr/bin/python
# -*- coding: utf-8 -*-

import base64
import re
from datetime import datetime, timedelta

import requests
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from enigma import eServiceReference
from requests.adapters import HTTPAdapter, Retry
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . import _
from . import bouquet_globals as glob
from .bmxStaticText import StaticText
from .plugin import cfg, HDR, SCREENWIDTH

try:
    from http.client import HTTPConnection

    HTTPConnection.debuglevel = 0
except ImportError:
    from httplib import HTTPConnection

    HTTPConnection.debuglevel = 0


class BmxCatchup(Screen):
    def __init__(self, session):
        if SCREENWIDTH.width() == 2560:
            skin = """
                <screen name="BMXCatchup" position="center,center" size="1600,1068" >

                <widget source="bmx_title" render="Label" position="0,0" size="1468,56" font="bmxbold;40" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" noWrap="1" transparent="1" zPosition="2" />

                <widget source="global.CurrentTime" render="Label" position="1468,0" size="132,56" font="bmxbold;40" foregroundColor="#ffffff" backgroundColor="#2a70a4" valign="center" halign="right" transparent="1" zPosition="2">
                    <convert type="ClockToText">Format:%H:%M | %A %-d %b</convert>
                </widget>

                <widget source="bmx_description" render="BMXRunningText" options="movetype=running,startpoint=0,direction=top,steptime=80,repeat=0,always=0,oneshot=0,startdelay=6000,wrap" position="0,64" size="1600,160"
                font="bmxregular;36" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" transparent="1" zPosition="2" />

                <widget source="epg_short_list" render="Listbox" position="0,268" size="1600,800" foregroundColor="#ffffff" backgroundColor="#2a70a4" foregroundColorSelected="#ffffff" backgroundColorSelected="#102e4b" scrollbarMode="showOnDemand" enableWrapAround="1" itemHeight="80" transparent="1" zPosition="4" >
                    <convert type="TemplatedMultiContent">{"template": [
                        MultiContentEntryText(pos = (20, 0), size = (300, 80), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1 ),
                        MultiContentEntryText(pos = (320, 0), size = (320, 80), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2),
                        MultiContentEntryText(pos = (640, 0), size = (960, 80), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 0),
                        ],
                        "fonts": [gFont("bmxregular", 36)],
                        "itemHeight": 80,
                        "scrollbarMode": "showOnDemand"
                        }</convert>
                </widget>

                </screen>"""

        elif SCREENWIDTH.width() > 1280:
            skin = """
                <screen name="BMXCatchup" position="center,center" size="1200,801" >

                <widget source="bmx_title" render="Label" position="0,0" size="1101,42" font="bmxbold;30" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" noWrap="1" transparent="1" zPosition="2" />

                <widget source="global.CurrentTime" render="Label" position="1101,0" size="99,42" font="bmxbold;30" foregroundColor="#ffffff" backgroundColor="#2a70a4" valign="center" halign="right" transparent="1" zPosition="2">
                    <convert type="ClockToText">Format:%H:%M | %A %-d %b</convert>
                </widget>

                <widget source="bmx_description" render="BMXRunningText" options="movetype=running,startpoint=0,direction=top,steptime=80,repeat=0,always=0,oneshot=0,startdelay=6000,wrap" position="0,48" size="1200,120"
                font="bmxregular;27" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" transparent="1" zPosition="2" />

                <widget source="epg_short_list" render="Listbox" position="0,201" size="1200,600" foregroundColor="#ffffff" backgroundColor="#2a70a4" foregroundColorSelected="#ffffff" backgroundColorSelected="#102e4b" scrollbarMode="showOnDemand" enableWrapAround="1" itemHeight="60" transparent="1" zPosition="4" >
                    <convert type="TemplatedMultiContent">{"template": [
                        MultiContentEntryText(pos = (15, 0), size = (225, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1 ),
                        MultiContentEntryText(pos = (240, 0), size = (240, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2),
                        MultiContentEntryText(pos = (480, 0), size = (720, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 0),
                        ],
                        "fonts": [gFont("bmxregular", 27)],
                        "itemHeight": 60,
                        "scrollbarMode": "showOnDemand"
                        }</convert>
                </widget>

                </screen>"""

        else:
            skin = """
                <screen name="BMXCatchup" position="center,center" size="800,534" >

                <widget source="bmx_title" render="Label" position="0,0" size="734,28" font="bmxbold;20" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" noWrap="1" transparent="1" zPosition="2" />

                <widget source="global.CurrentTime" render="Label" position="734,0" size="66,28" font="bouquetrbold;20" foregroundColor="#ffffff" backgroundColor="#2a70a4" valign="center" halign="right" transparent="1" zPosition="2">
                    <convert type="ClockToText">Format:%H:%M | %A %-d %b</convert>
                </widget>

                <widget source="bmx_description" render="BMXRunningText" options="movetype=running,startpoint=0,direction=top,steptime=80,repeat=0,always=0,oneshot=0,startdelay=6000,wrap" position="0,32" size="800,80"
                font="bmxregular;18" foregroundColor="#ffffff" backgroundColor="#2a70a4" halign="left" transparent="1" zPosition="2" />

                <widget source="epg_short_list" render="Listbox" position="0,134" size="800,400" foregroundColor="#ffffff" backgroundColor="#2a70a4" foregroundColorSelected="#ffffff" backgroundColorSelected="#102e4b" scrollbarMode="showOnDemand" enableWrapAround="1" itemHeight="40" transparent="1" zPosition="4" >
                    <convert type="TemplatedMultiContent">{"template": [
                        MultiContentEntryText(pos = (10, 0), size = (150, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1 ),
                        MultiContentEntryText(pos = (160, 0), size = (160, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2),
                        MultiContentEntryText(pos = (320, 0), size = (540, 60), font=0, color = 0x00ffffff, color_sel = 0x00ffffff, backcolor_sel = None, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 0),
                        ],
                        "fonts": [gFont("bmxregular", 18)],
                        "itemHeight": 40,
                        "scrollbarMode": "showOnDemand"
                        }</convert>
                </widget>

                </screen>"""

        Screen.__init__(self, session)
        self.session = session

        self.skin = skin

        self.current_selection = 0

        self.epg_short_list = []

        self["epg_short_list"] = List(self.epg_short_list, enableWrapAround=True)
        self["epg_short_list"].onSelectionChanged.append(self.display_short_epg)

        self["actions"] = ActionMap(["BMXActions"], {
            "ok": self.play,
            "cancel": self.quit,
            "red": self.quit
        }, -2)

        self.setup_title = _("TV Archive: %s" % glob.NAME.lstrip(cfg.catchup_prefix.value))

        self["bmx_title"] = StaticText()
        self["bmx_description"] = StaticText()

        self.ref_url = ""
        self.ref_stream = ""
        self.ref_stream_num = ""
        self.username = ""
        self.password = ""
        self.domain = ""

        self.ref_url = glob.CURRENT_REF.getPath()
        # http://domain.xyx:0000/live/user/pass/12345.ts

        if "/live/" not in self.ref_url:
            return

        self.ref_stream = self.ref_url.split("/")[-1]
        # 12345.ts

        self.ref_stream_num = int(self.ref_stream.split(".")[0])
        # 12345

        # get domain, username, password from path
        match1 = False
        if re.search(r"(https|http):\/\/[^\/]+\/(live|movie|series)\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", self.ref_url) is not None:
            match1 = True

        match2 = False
        if re.search(r"(https|http):\/\/[^\/]+\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", self.ref_url) is not None:
            match2 = True

        if match1:
            self.username = re.search(r"[^\/]+(?=\/[^\/]+\/\d+\.)", self.ref_url).group()
            self.password = re.search(r"[^\/]+(?=\/\d+\.)", self.ref_url).group()
            self.domain = re.search(r"(https|http):\/\/[^\/]+", self.ref_url).group()

        elif match2:
            self.username = re.search(r"[^\/]+(?=\/[^\/]+\/[^\/]+$)", self.ref_url).group()
            self.password = re.search(r"[^\/]+(?=\/[^\/]+$)", self.ref_url).group()
            self.domain = re.search(r"(https|http):\/\/[^\/]+", self.ref_url).group()

        self.simple_url = "%s/player_api.php?username=%s&password=%s&action=get_simple_data_table&stream_id=%s" % (self.domain, self.username, self.password, self.ref_stream_num)
        self.player_api = "%s/player_api.php?username=%s&password=%s" % (self.domain, self.username, self.password)

        self.onFirstExecBegin.append(self.create_setup)
        self.onLayoutFinish.append(self.__layout_finished)

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def quit(self):
        self.close()

    def create_setup(self):
        self["bmx_title"].setText("")
        self["bmx_description"].setText("")
        self.download_player_api()

    def download_player_api(self):
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""

        try:
            r = http.get(self.player_api, headers=HDR, timeout=10, verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                try:
                    response = r.json()
                except Exception as e:
                    print(e)

        except Exception as e:
            print(e)

        self.server_offset = 0

        if response:
            if "user_info" in response:
                if "server_info" in response:
                    if "time_now" in response["server_info"]:
                        try:
                            time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            try:
                                time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d %H-%M-%S")
                            except Exception:
                                time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d-%H:%M:%S")

                        self.server_offset = (datetime.now().hour - time_now_datestamp.hour)
                        # print("*** server_offset ***", self.server_offset)

        self.download_simple_data()

    def download_simple_data(self):
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""

        try:
            r = http.get(self.simple_url, headers=HDR, timeout=10, verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                try:
                    response = r.json()
                except Exception as e:
                    print(e)

        except Exception as e:
            print(e)

        if response:
            short_epg_json = response
            index = 0
            self.epg_short_list = []

            if "epg_listings" not in short_epg_json:
                self.session.open(MessageBox, _("Catchup currently not available. Missing EPG data"), type=MessageBox.TYPE_INFO, timeout=5)
                return

            else:
                for listing in short_epg_json["epg_listings"]:
                    if ("has_archive" in listing and listing["has_archive"] == 1) or ("now_playing" in listing and listing["now_playing"] == 1):
                        title = ""
                        description = ""
                        epg_date_all = ""
                        epg_time_all = ""
                        start = ""
                        end = ""

                        catchup_start = int(cfg.catchup_start.getValue())
                        catchup_end = int(cfg.catchup_end.getValue())

                        if "title" in listing:
                            title = base64.b64decode(listing["title"]).decode("utf-8")

                        if "description" in listing:
                            description = base64.b64decode(listing["description"]).decode("utf-8")

                        if listing["start"] and listing["end"]:
                            start = listing["start"]
                            end = listing["end"]

                            start_datetime_original = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                            start_datetime_offset = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset)
                            start_datetime_margin = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset) - timedelta(minutes=catchup_start)

                            try:
                                end_datetime_offset = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset)
                                end_datetime_margin = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset) + timedelta(minutes=catchup_end)
                            except Exception:
                                try:
                                    end = listing["stop"]
                                    end_datetime_offset = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset)
                                    end_datetime_margin = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.server_offset) + timedelta(minutes=catchup_end)
                                except Exception:
                                    return

                            epg_date_all = start_datetime_offset.strftime("%a %d/%m")
                            epg_time_all = (str(start_datetime_offset.strftime("%H:%M")) + " - " + str(end_datetime_offset.strftime("%H:%M")))

                        epg_duration = int((end_datetime_margin - start_datetime_margin).total_seconds() / 60.0)

                        url_datestring = str(start_datetime_original.strftime("%Y-%m-%d:%H-%M"))

                        self.epg_short_list.append(build_catchup_epg_list_entry(str(epg_date_all), str(epg_time_all), str(title), str(description), str(url_datestring), str(epg_duration), index, self.ref_stream_num))

                        index += 1

                self.epg_short_list.reverse()
                self["epg_short_list"].setList(self.epg_short_list)

                self.display_short_epg()

    def reverse(self):
        self.epg_short_list.reverse()
        self["epg_short_list"].setList(self.epg_short_list)

    def display_short_epg(self):
        if self["epg_short_list"].getCurrent():
            title = str(self["epg_short_list"].getCurrent()[0])
            description = str(self["epg_short_list"].getCurrent()[3])
            timeall = str(self["epg_short_list"].getCurrent()[2])
            self["bmx_title"].setText(timeall + " " + title)
            self["bmx_description"].setText(description)
            self.current_selection = self["epg_short_list"].getIndex()

    def play(self):
        if self["epg_short_list"].getCurrent():
            playurl = "%s/streaming/timeshift.php?username=%s&password=%s&stream=%s&start=%s&duration=%s" % (self.domain, self.username, self.password, self.epg_short_list[self.current_selection][7], self.epg_short_list[self.current_selection][4], self.epg_short_list[self.current_selection][5])
            stream_type = 4097
            sref = eServiceReference(stream_type, 0, playurl)
            sref.setName(self.epg_short_list[self.current_selection][2])
            self.session.open(MoviePlayer, sref)


def build_catchup_epg_list_entry(date_all, time_all, title, description, start, duration, index, refstreamnum):
    return (title, date_all, time_all, description, start, duration, index, refstreamnum,)
