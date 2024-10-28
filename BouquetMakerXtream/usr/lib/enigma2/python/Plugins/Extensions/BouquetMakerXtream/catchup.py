#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from .bmxStaticText import StaticText
from .plugin import cfg, screenwidth

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

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate'
}


class BmxCatchup(Screen):
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

        self.current_selection = 0

        self.epg_short_list = []

        self["epg_short_list"] = List(self.epg_short_list, enableWrapAround=True)
        self["epg_short_list"].onSelectionChanged.append(self.displayShortEpg)

        self["actions"] = ActionMap(["BMXActions"], {
            "ok": self.play,
            "cancel": self.quit,
            "red": self.quit
        }, -2)

        self.setup_title = _("TV Archive: %s") % glob.name.lstrip(cfg.catchup_prefix.value)

        self["bmx_title"] = StaticText("")
        self["bmx_description"] = StaticText("")

        self.ref_url = ""
        self.ref_stream = ""
        self.ref_stream_num = ""
        self.username = ""
        self.password = ""
        self.domain = ""

        self.ref_url = glob.currentref.getPath()
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
        response = ""

        with requests.Session() as http:
            http.mount("http://", adapter)
            http.mount("https://", adapter)

            try:
                r = http.get(self.player_api, headers=hdr, timeout=10, verify=False)
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
                            time_now_datestamp = datetime.strptime(
                                str(response["server_info"]["time_now"]), "%Y-%m-%d %H:%M:%S"
                            )
                        except:
                            try:
                                time_now_datestamp = datetime.strptime(
                                    str(response["server_info"]["time_now"]), "%Y-%m-%d %H-%M-%S"
                                )
                            except:
                                time_now_datestamp = datetime.strptime(
                                    str(response["server_info"]["time_now"]), "%Y-%m-%d-%H:%M:%S"
                                )

                        self.server_offset = datetime.now().hour - time_now_datestamp.hour
                        # print("*** server_offset ***", self.server_offset)

        self.downloadSimpleData()

    def downloadSimpleData(self):
        retries = Retry(total=3, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)

        with requests.Session() as http:
            http.mount("http://", adapter)
            http.mount("https://", adapter)

            try:
                response = http.get(self.simple_url, headers=hdr, timeout=(10, 20), verify=False)
                response.raise_for_status()

                if response.status_code == requests.codes.ok:
                    short_epg_json = response.json()

            except Exception as e:
                print(e)
                return

        if short_epg_json:
            if "epg_listings" not in short_epg_json or not short_epg_json["epg_listings"]:
                self.session.open(MessageBox, _("Catchup currently not available. Missing EPG data"), type=MessageBox.TYPE_INFO, timeout=5)
                return

            index = 0
            self.epg_short_list = []

            shift = self.server_offset
            catchupstart = int(cfg.catchup_start.value)
            catchupend = int(cfg.catchup_end.value)

            for listing in short_epg_json["epg_listings"]:
                if "has_archive" in listing and listing["has_archive"] == 1 or "now_playing" in listing and listing["now_playing"] == 1:

                    title = base64.b64decode(listing.get("title", "")).decode("utf-8")
                    description = base64.b64decode(listing.get("description", "")).decode("utf-8")
                    start = listing.get("start", "")
                    end = listing.get("end", "")
                    stop = listing.get("stop", "")

                    if start:
                        start_datetime_original = self.parse_datetime(start)
                        if start_datetime_original:
                            start_datetime = start_datetime_original + timedelta(hours=shift)
                            start_datetime_original_margin = start_datetime_original - timedelta(minutes=catchupstart)
                        else:
                            print("Error parsing start datetime")
                            continue
                    if end:
                        end_datetime = self.parse_datetime(end)
                        if end_datetime:
                            end_datetime += timedelta(hours=shift)
                        else:
                            print("Error parsing end datetime")
                            continue
                    elif stop:
                        stop_datetime = self.parse_datetime(stop)
                        if stop_datetime:
                            end_datetime = stop_datetime + timedelta(hours=shift)
                        else:
                            print("Error parsing stop datetime")
                            continue
                    else:
                        print("Error: Missing end or stop time")
                        continue

                    if start_datetime and end_datetime:

                        start_datetime_margin = start_datetime - timedelta(minutes=catchupstart)
                        end_datetime_margin = end_datetime + timedelta(minutes=catchupend)

                        epg_date_all = start_datetime.strftime("%a %d/%m")

                        epg_time_all = "{} - {}".format(start_datetime.strftime("%H:%M"), end_datetime.strftime("%H:%M"))

                        epg_duration = int((end_datetime_margin - start_datetime_margin).total_seconds() / 60.0)

                        url_datestring = start_datetime_original_margin.strftime("%Y-%m-%d:%H-%M")

                        # url_datestring = start_datetime_margin.strftime("%Y-%m-%d:%H-%M")

                        self.epg_short_list.append(buildCatchupEpgListEntry(str(epg_date_all), str(epg_time_all), str(title), str(description), str(url_datestring), str(epg_duration), index, self.ref_stream_num))

                        index += 1

                self.epg_short_list.reverse()
                self["epg_short_list"].setList(self.epg_short_list)

                self.displayShortEpg()

    def parse_datetime(self, datetime_str):
        time_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H-%M-%S", "%Y-%m-%d-%H:%M:%S", "%Y- %m-%d %H:%M:%S"]

        for time_format in time_formats:
            try:
                return datetime.strptime(datetime_str, time_format)
            except ValueError:
                pass
        return ""  # Return None if none of the formats match

    def reverse(self):
        self.epg_short_list.reverse()
        self["epg_short_list"].setList(self.epg_short_list)

    def displayShortEpg(self):
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


def buildCatchupEpgListEntry(date_all, time_all, title, description, start, duration, index, refstreamnum):
    return (title, date_all, time_all, description, start, duration, index, refstreamnum,)
