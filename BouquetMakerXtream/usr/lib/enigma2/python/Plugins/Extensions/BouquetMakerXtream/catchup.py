#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob

from .plugin import cfg, hdr, screenwidth
from .bmxStaticText import StaticText

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from datetime import datetime, timedelta
from enigma import eServiceReference
from requests.adapters import HTTPAdapter, Retry
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

import base64
import re
import requests

try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0
requests.packages.urllib3.disable_warnings()


class BMX_Catchup(Screen):

    def __init__(self, session):

        if screenwidth.width() == 2560:
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

        elif screenwidth.width() > 1280:
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

        self.currentSelection = 0

        self.epgshortlist = []

        self["epg_short_list"] = List(self.epgshortlist, enableWrapAround=True)
        self["epg_short_list"].onSelectionChanged.append(self.displayShortEPG)

        self["actions"] = ActionMap(["BMXActions"], {
            "ok": self.play,
            "cancel": self.quit,
            "red": self.quit
        }, -2)

        self.setup_title = _("TV Archive: %s" % glob.name.lstrip(cfg.catchupprefix.value))

        self["bmx_title"] = StaticText()
        self["bmx_description"] = StaticText()

        self.refurl = ""
        self.refstream = ""
        self.refstreamnum = ""
        self.username = ""
        self.password = ""
        self.domain = ""
        self.error_message = ""
        self.isCatchupChannel = False

        self.refurl = glob.currentref.getPath()
        # http://domain.xyx:0000/live/user/pass/12345.ts

        if "/live/" not in self.refurl:
            return

        self.refstream = self.refurl.split("/")[-1]
        # 12345.ts

        self.refstreamnum = int(self.refstream.split(".")[0])
        # 12345

        # get domain, username, password from path
        match1 = False
        if re.search(r"(https|http):\/\/[^\/]+\/(live|movie|series)\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", self.refurl) is not None:
            match1 = True

        match2 = False
        if re.search(r"(https|http):\/\/[^\/]+\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", self.refurl) is not None:
            match2 = True

        if match1:
            self.username = re.search(r"[^\/]+(?=\/[^\/]+\/\d+\.)", self.refurl).group()
            self.password = re.search(r"[^\/]+(?=\/\d+\.)", self.refurl).group()
            self.domain = re.search(r"(https|http):\/\/[^\/]+", self.refurl).group()

        elif match2:
            self.username = re.search(r"[^\/]+(?=\/[^\/]+\/[^\/]+$)", self.refurl).group()
            self.password = re.search(r"[^\/]+(?=\/[^\/]+$)", self.refurl).group()
            self.domain = re.search(r"(https|http):\/\/[^\/]+", self.refurl).group()

        self.simpleurl = "%s/player_api.php?username=%s&password=%s&action=get_simple_data_table&stream_id=%s" % (self.domain, self.username, self.password, self.refstreamnum)
        self.playerapi = "%s/player_api.php?username=%s&password=%s" % (self.domain, self.username, self.password)

        self.onFirstExecBegin.append(self.createSetup)
        self.onLayoutFinish.append(self.__layoutFinished)

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def quit(self):
        self.close()

    def createSetup(self):
        self["bmx_title"].setText("")
        self["bmx_description"].setText("")
        self.downloadPlayerApi()

    def downloadPlayerApi(self):
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""

        try:
            r = http.get(self.playerapi, headers=hdr, timeout=10, verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                try:
                    response = r.json()
                except Exception as e:
                    print(e)

        except Exception as e:
            print(e)

        self.serveroffset = 0

        if response:
            if "user_info" in response:
                if "server_info" in response:
                    if "time_now" in response["server_info"]:
                        try:
                            time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d %H:%M:%S")
                        except:
                            try:
                                time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d %H-%M-%S")
                            except:
                                time_now_datestamp = datetime.strptime(str(response["server_info"]["time_now"]), "%Y-%m-%d-%H:%M:%S")

                        self.serveroffset = datetime.now().hour - time_now_datestamp.hour
                        print("*** serveroffset ***", self.serveroffset)

        self.downloadSimpleData()

    def downloadSimpleData(self):
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""

        try:
            r = http.get(self.simpleurl, headers=hdr, timeout=10, verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                try:
                    response = r.json()
                except Exception as e:
                    print(e)

        except Exception as e:
            print(e)

        if response:
            shortEPGJson = response
            index = 0
            self.epgshortlist = []

            if "epg_listings" not in shortEPGJson:

                self.session.open(MessageBox, _("Catchup currently not available. Missing EPG data"), type=MessageBox.TYPE_INFO, timeout=5)
                return

            else:
                for listing in shortEPGJson["epg_listings"]:
                    if ("has_archive" in listing and listing["has_archive"] == 1) or ("now_playing" in listing and listing["now_playing"] == 1):

                        title = ""
                        description = ""
                        epg_date_all = ""
                        epg_time_all = ""
                        start = ""
                        end = ""

                        catchupstart = int(cfg.catchupstart.getValue())
                        catchupend = int(cfg.catchupend.getValue())

                        if "title" in listing:
                            title = base64.b64decode(listing["title"]).decode("utf-8")

                        if "description" in listing:
                            description = base64.b64decode(listing["description"]).decode("utf-8")

                        if listing["start"] and listing["end"]:

                            start = listing["start"]
                            end = listing["end"]

                            start_datetime_original = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                            start_datetime_offset = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset)
                            start_datetime_margin = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset) - timedelta(minutes=catchupstart)

                            try:
                                end_datetime_offset = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset)
                                end_datetime_margin = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset) + timedelta(minutes=catchupend)
                            except:
                                try:
                                    end = listing["stop"]
                                    end_datetime_offset = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset)
                                    end_datetime_margin = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") + timedelta(hours=self.serveroffset) + timedelta(minutes=catchupend)
                                except:
                                    return

                            epg_date_all = start_datetime_offset.strftime("%a %d/%m")
                            epg_time_all = str(start_datetime_offset.strftime("%H:%M")) + " - " + str(end_datetime_offset.strftime("%H:%M"))

                        epg_duration = int((end_datetime_margin - start_datetime_margin).total_seconds() / 60.0)

                        url_datestring = str(start_datetime_original.strftime("%Y-%m-%d:%H-%M"))

                        self.epgshortlist.append(buildCatchupEPGListEntry(str(epg_date_all), str(epg_time_all), str(title), str(description), str(url_datestring), str(epg_duration), index, self.refstreamnum))

                        index += 1

                self.epgshortlist.reverse()
                self["epg_short_list"].setList(self.epgshortlist)

                self.displayShortEPG()

    def reverse(self):
        self.epgshortlist.reverse()
        self["epg_short_list"].setList(self.epgshortlist)

    def displayShortEPG(self):
        if self["epg_short_list"].getCurrent():
            title = str(self["epg_short_list"].getCurrent()[0])
            description = str(self["epg_short_list"].getCurrent()[3])
            timeall = str(self["epg_short_list"].getCurrent()[2])
            self["bmx_title"].setText(timeall + " " + title)
            self["bmx_description"].setText(description)
            self.currentSelection = self["epg_short_list"].getIndex()

    def play(self):
        if self["epg_short_list"].getCurrent():
            playurl = "%s/streaming/timeshift.php?username=%s&password=%s&stream=%s&start=%s&duration=%s" % (self.domain, self.username, self.password, self.epgshortlist[self.currentSelection][7], self.epgshortlist[self.currentSelection][4], self.epgshortlist[self.currentSelection][5])
            streamtype = 4097
            sref = eServiceReference(streamtype, 0, playurl)
            sref.setName(self.epgshortlist[self.currentSelection][2])
            self.session.open(MoviePlayer, sref)


def buildCatchupEPGListEntry(date_all, time_all, title, description, start, duration, index, refstreamnum):
    return (title, date_all, time_all, description, start, duration, index, refstreamnum)
