#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import globalfunctions as bmxfunctions
from . import bouquet_globals as glob

from .plugin import cfg, skin_directory, hdr, pythonVer, playlists_json, epgimporter

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer, eDVBDB

from requests.adapters import HTTPAdapter, Retry
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

try:
    from xml.dom import minidom
except:
    pass

import json
import os
import re
import requests

try:
    from urllib import quote
except:
    from urllib.parse import quote


try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0

requests.packages.urllib3.disable_warnings()


class BouquetMakerXtream_BuildBouquets(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "progress.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = (_("Building Bouquets"))

        # self.current_playlist = glob.current_playlist

        self.categories = []

        self["action"] = Label(_("Building Bouquets..."))
        self["status"] = Label("")
        self["progress"] = ProgressBar()
        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
            "cancel": self.keyCancel,
        }, -2)

        self.safefilename = self.safe_name(glob.current_playlist["playlist_info"]["name"])

        self.unique_ref = 0
        for j in str(glob.current_playlist["playlist_info"]["full_url"]).lower():
            value = ord(j)
            self.unique_ref += value

        self.progressvalue = 0
        self.progressrange = 1
        self.processing = False

        if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
            self.protocol = glob.current_playlist["playlist_info"]["protocol"]
            self.domain = glob.current_playlist["playlist_info"]["domain"]
            self.port = glob.current_playlist["playlist_info"]["port"]
            self.streamtype = glob.current_playlist["settings"]["livetype"]

            if self.port:
                self.host = self.protocol + self.domain + ":" + str(self.port)
            else:
                self.host = self.protocol + self.domain

            self.host_encoded = quote(self.host)

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.get_api = str(glob.current_playlist["playlist_info"]["full_url"])
                self.player_api = str(glob.current_playlist["playlist_info"]["player_api"])
                self.xmltv_api = str(glob.current_playlist["playlist_info"]["xmltv_api"])

                self.LiveStreamsUrl = self.player_api + "&action=get_live_streams"
                self.VodStreamsUrl = self.player_api + "&action=get_vod_streams"
                self.SeriesUrl = self.player_api + "&action=get_series"

                self.username = glob.current_playlist["playlist_info"]["username"]
                self.password = glob.current_playlist["playlist_info"]["password"]
                self.output = glob.current_playlist["playlist_info"]["output"]

                self.simple = str(self.host) + "/" + "get.php?username=" + str(self.username) + "&password=" + str(self.password) + "&type=simple&output=" + str(self.output)

                # self.progressrange += 2

        self.full_url = glob.current_playlist["playlist_info"]["full_url"]

        # init variables
        self.livecategories = []
        self.livecategoriescount = 0
        self.livestreams = []
        self.livestreamscount = 0

        self.vodcategories = []
        self.vodcategoriescount = 0
        self.vodstreams = []
        self.vodstreamscount = 0

        self.seriescategories = []
        self.seriescategoriescount = 0
        self.seriesstreams = []
        self.seriesstreamscount = 0

        self.totalcount = 0

        if glob.current_playlist["settings"]["showlive"] is True:
            self.livecategories = glob.current_playlist["data"]["live_categories"]
            self.livecategoriescount = len(self.livecategories)

            self.livestreams = glob.current_playlist["data"]["live_streams"]
            self.livestreamscount = len(self.livestreams)

            if (glob.current_playlist["settings"]["livecategoryorder"] == "alphabetical"):
                self.livecategories = sorted(self.livecategories, key=lambda k: k["category_name"].lower())

            self.progressrange += 1
            # self.progressrange += self.livecategoriescount

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.progressrange += 3

        if glob.current_playlist["settings"]["showvod"] is True:
            self.vodcategories = glob.current_playlist["data"]["vod_categories"]
            self.vodcategoriescount = len(self.vodcategories)

            self.vodstreams = glob.current_playlist["data"]["vod_streams"]
            self.vodstreamscount = len(self.vodstreams)

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.vodcategories = sorted(self.vodcategories, key=lambda k: k["category_name"].lower())

            self.progressrange += 1
            # self.progressrange += self.vodcategoriescount

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.progressrange += 1

        if glob.current_playlist["settings"]["showseries"] is True:
            self.seriescategories = glob.current_playlist["data"]["series_categories"]
            self.seriescategoriescount = len(self.seriescategories)

            self.seriesstreams = glob.current_playlist["data"]["series_streams"]
            self.seriesstreamscount = len(self.seriesstreams)

            if (glob.current_playlist["settings"]["vodcategoryorder"] == "alphabetical"):
                self.seriescategories = sorted(self.seriescategories, key=lambda k: k["category_name"].lower())

            self.progressrange += 1
            # self.progressrange += self.seriescategoriescount

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.progressrange += 2

        self.starttimer = eTimer()
        try:
            self.starttimer_conn = self.starttimer.timeout.connect(self.start)
        except:
            self.starttimer.callback.append(self.start)
        self.starttimer.start(100, True)

    def keyCancel(self):
        self.close()

    def nextjob(self, actiontext, function):
        # print("*** function ***", function)
        self.processing = True
        self["action"].setText(actiontext)
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(function)
        except:
            self.timer.callback.append(function)
        self.timer.start(10, True)

    def refresh_bouquets(self):
        print("*** refreshing bouquets **")
        eDVBDB.getInstance().reloadServicelist()
        eDVBDB.getInstance().reloadBouquets()

    def safe_name(self, name):
        safeName = re.sub(r'[\<\>\:\"\/\\\|\?\*]', "_", name)
        safeName = re.sub(r" ", "_", safeName)
        safeName = re.sub(r"_+", "_", safeName)
        return safeName

    def start(self):
        self["progress"].setRange((0, self.progressrange))
        self["progress"].setValue(self.progressvalue)

        self.nextjob(_("Deleting existing data..."), self.delete_existing_refs)

        self.endtimer = eTimer()
        try:
            self.endtimer_conn = self.endtimer.timeout.connect(self.checkfinished)
        except:
            self.endtimer.callback.append(self.checkfinished)
        self.endtimer.start(500, False)

    def checkfinished(self):
        if self.processing is False:
            self.endtimer.stop()
            self.finished()

    def delete_existing_refs(self):
        print("*** delete_existing_refs ***")
        safeName = self.safefilename

        with open("/etc/enigma2/bouquets.tv", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            for line in lines:
                if "bouquetmakerxtream_live_" + str(safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_vod_" + str(safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_series_" + str(safeName) + "_" in line:
                    continue
                if "bouquetmakerxtream_" + str(safeName) + "_" in line:

                    continue
                f.write(line)
            f.truncate()

        bmxfunctions.purge("/etc/enigma2", "bouquetmakerxtream_live_" + str(safeName) + "_")
        bmxfunctions.purge("/etc/enigma2", "bouquetmakerxtream_vod_" + str(safeName) + "_")
        bmxfunctions.purge("/etc/enigma2", "bouquetmakerxtream_series_" + str(safeName) + "_")
        bmxfunctions.purge("/etc/enigma2", str(safeName) + str(".tv"))

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

        if epgimporter is True:
            bmxfunctions.purge("/etc/epgimport", "bouquetmakerxtream." + str(safeName))

        if glob.current_playlist["settings"]["showlive"]:
            self.nextjob(_("Processing live data..."), self.process_live)

        elif glob.current_playlist["settings"]["showvod"]:
            self.nextjob(_("Processing VOD data..."), self.process_vod)

        elif glob.current_playlist["settings"]["showseries"]:
            self.nextjob(_("Processing series data..."), self.process_series)

    def download_url(self, url, ext):
        print("*** url ***", url)
        r = ""
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        r = ""
        try:
            r = http.get(url, headers=hdr, timeout=(10, 30), verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                try:
                    if ext == "json":
                        response = r.json()
                    if ext == "xml":
                        response = r.content
                    if ext == "text":
                        response = r.content
                    return response
                except Exception as e:
                    print(e)
                    return ""

        except Exception as e:
            print(e)

        return ""

    def process_live(self):
        print("*** process_live ***")

        self.livestreamdata = ""

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.livestreamdata = self.downloadLiveStreams()
            self.progressvalue += 1
            self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "external":
            pass

        if glob.current_playlist["playlist_info"]["playlisttype"] == "local":
            pass

        if self.livestreamdata:
            # print("*** true ***")
            for category in self.livecategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"]:
                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    self.build_bouquet_tv_file("live", bouquetTitle)

                    self.totalcount += 1
                    stringbuilder = ""
                    stringlist = []

                    if glob.current_playlist["settings"]["prefixname"] is True:
                        stringbuilder += "#NAME " + self.safefilename + " - " + category["category_name"] + "\n"
                    else:
                        stringbuilder += "#NAME " + category["category_name"] + "\n"

                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    for stream in self.livestreamdata:

                        if str(category["category_id"]) == str(stream["category_id"]):
                            stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])
                            # stringbuilder += stream["bouquetString"]

                    if (glob.current_playlist["settings"]["livestreamorder"] == "alphabetical"):
                        stringlist.sort(key=lambda x: x[1].lower())

                    if (glob.current_playlist["settings"]["livestreamorder"] == "added"):
                        stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in stringlist:
                        stringbuilder += string[0]

                    self.build_userbouquets("live", bouquetTitle, stringbuilder)
                    # self.progressvalue += 1

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

        print("**** starting xmltv source ***")
        if epgimporter:
            self.nextjob(_("Building EPG Source File..."), self.build_xmltv_source)

        if glob.current_playlist["settings"]["showvod"]:
            self.nextjob(_("Processing VOD data..."), self.process_vod)

        elif glob.current_playlist["settings"]["showseries"]:
            self.nextjob(_("Processing series data..."), self.process_series)

        else:
            self.processing = False

    def downloadLiveStreams(self):
        print("*** downloadLiveStreams ***")
        streamlist = []
        if self.livecategoriescount == len(glob.current_playlist["data"]["live_categories_hidden"]):
            return streamlist

        url = str(self.player_api) + "&action=get_live_streams"
        result = self.download_url(url, "json")

        streamlist = []

        if result:
            try:
                channellist_all = result

                for channel in channellist_all:

                    stream_id = str(channel["stream_id"])

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["live_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["live_streams_hidden"]:

                        name = channel["name"]
                        name = name.replace(":", "").replace('"', "").strip("-")

                        if "tv_archive" in channel:
                            catchup = int(channel["tv_archive"])
                        else:
                            catchup = 0

                        if cfg.catchup.value is True and catchup == 1:
                            name = str(cfg.catchupprefix.value) + str(name)

                        channelid = str(channel["epg_channel_id"])
                        if channelid and "&" in channelid:
                            channelid = channelid.replace("&", "&amp;")

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        serviceref = "1:0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:" + "http%3a//example.m3u8"
                        custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                        if "custom_sid" in channel:
                            if channel["custom_sid"] and channel["custom_sid"] != "null" and channel["custom_sid"] != "None" and channel["custom_sid"] is not None:

                                if channel["custom_sid"][0].isdigit():
                                    channel["custom_sid"] = channel["custom_sid"][1:]

                                serviceref = str(":".join(channel["custom_sid"].split(":")[:7])) + ":0:0:0:" + "http%3a//example.m3u8"
                                custom_sid = channel["custom_sid"]

                        xml_str = ""
                        if channelid and channelid != "None":
                            xml_str = '\t<channel id="' + str(channelid) + '">' + str(self.streamtype) + str(serviceref) + '</channel><!-- ' + str(name) + ' -->\n'

                        bouquetString = ""
                        bouquetString += "#SERVICE " + str(self.streamtype) + str(custom_sid) + str(self.host_encoded) + "/live/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(self.output) + ":" + str(name) + "\n"
                        bouquetString += "#DESCRIPTION " + str(name) + "\n"

                        streamlist.append({"category_id": str(channel["category_id"]), "xml_str": str(xml_str), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})
                return streamlist
            except Exception as e:
                print(e)
        else:
            return streamlist

    def process_vod(self):
        print("*** process_vod ***")
        self.vodstreamdata = ""
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.vodstreamdata = self.downloadVodStreams()
            self.progressvalue += 1
            self["progress"].setValue(self.progressvalue)
        if glob.current_playlist["playlist_info"]["playlisttype"] == "external":
            pass
        if glob.current_playlist["playlist_info"]["playlisttype"] == "local":
            pass

        if self.vodstreamdata:
            for category in self.vodcategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"]:
                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    self.build_bouquet_tv_file("vod", bouquetTitle)

                    self.totalcount += 1
                    stringbuilder = ""
                    stringlist = []

                    if glob.current_playlist["settings"]["prefixname"] is True:
                        stringbuilder += "#NAME " + self.safefilename + "-VOD- " + category["category_name"] + "\n"
                    else:
                        stringbuilder += "#NAME " + "VOD " + category["category_name"] + "\n"

                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    for stream in self.vodstreamdata:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])
                            # stringbuilder += stream["bouquetString"]

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                        stringlist.sort(key=lambda x: x[1].lower())

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                        stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in stringlist:
                        stringbuilder += string[0]

                    self.build_userbouquets("vod", bouquetTitle, stringbuilder)
                    # self.progressvalue += 1

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["settings"]["showseries"]:
            self.nextjob(_("Processing series data..."), self.process_series)

        else:
            self.processing = False

    def downloadVodStreams(self):
        print("*** downloadVodStreams ***")
        streamlist = []
        if self.vodcategoriescount == len(glob.current_playlist["data"]["vod_categories_hidden"]):
            return streamlist

        url = str(self.player_api) + "&action=get_vod_streams"
        result = self.download_url(url, "json")

        if result:
            try:
                channellist_all = result

                for channel in channellist_all:
                    stream_id = str(channel["stream_id"])

                    if str(channel["category_id"]) not in glob.current_playlist["data"]["vod_categories_hidden"] and str(channel["stream_id"]) not in glob.current_playlist["data"]["vod_streams_hidden"]:
                        extension = channel["container_extension"]

                        name = channel["name"]
                        name = name.replace(":", "").replace('"', "").strip("-")

                        bouquet_id1 = 0
                        calc_remainder = int(stream_id) // 65535
                        bouquet_id1 = bouquet_id1 + calc_remainder
                        bouquet_id2 = int(stream_id) - int(calc_remainder * 65535)

                        custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"

                        bouquetString = ""
                        bouquetString += "#SERVICE " + str(self.streamtype) + str(custom_sid) + str(self.host_encoded) + "/movie/" + str(self.username) + "/" + str(self.password) + "/" + str(stream_id) + "." + str(extension) + ":" + str(name) + "\n"
                        bouquetString += "#DESCRIPTION " + str(name) + "\n"

                        streamlist.append({"category_id": str(channel["category_id"]), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["added"])})
                return streamlist
            except Exception as e:
                print(e)
        else:
            return streamlist

    def process_series(self):
        print("*** process_series ***")
        self.seriesstreamdata = ""
        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.seriesstreamdata = self.downloadSeriesStreams()
            self.progressvalue += 2
            self["progress"].setValue(self.progressvalue)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "external":
            pass
        if glob.current_playlist["playlist_info"]["playlisttype"] == "local":
            pass

        if self.seriesstreamdata:
            for category in self.seriescategories:
                if str(category["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"]:
                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    self.build_bouquet_tv_file("series", bouquetTitle)

                    self.totalcount += 1
                    stringbuilder = ""
                    stringlist = []

                    if glob.current_playlist["settings"]["prefixname"] is True:
                        stringbuilder += "#NAME " + self.safefilename + "-Series- " + category["category_name"] + "\n"
                    else:
                        stringbuilder += "#NAME " + "Series " + category["category_name"] + "\n"

                    bouquetTitle = self.safefilename + "_" + self.safe_name(category["category_name"])
                    for stream in self.seriesstreamdata:
                        if str(category["category_id"]) == str(stream["category_id"]):
                            stringlist.append([str(stream["bouquetString"]), str(stream["name"]), str(stream["added"])])
                            # stringbuilder += stream["bouquetString"]

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "alphabetical"):
                        stringlist.sort(key=lambda x: x[1].lower())

                    if (glob.current_playlist["settings"]["vodstreamorder"] == "added"):
                        stringlist.sort(key=lambda x: x[2].lower(), reverse=True)

                    for string in stringlist:
                        stringbuilder += string[0]

                    self.build_userbouquets("series", bouquetTitle, stringbuilder)
                    # self.progressvalue += 1

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

        self.processing = False

    def downloadSeriesStreams(self):
        print("download get_series")

        streamlist = []
        if self.seriescategoriescount == len(glob.current_playlist["data"]["series_categories_hidden"]):
            return streamlist

        url = str(self.player_api) + "&action=get_series"
        seriesstreamresult = self.download_url(url, "json")

        # download get.api type=simple
        url = str(self.simple)
        seriessimpleresult = self.download_url(url, "text")

        if seriessimpleresult and seriesstreamresult:

            if "#EXTM3U" in str(seriessimpleresult):
                self.session.open(MessageBox, _("Your provider does not have the 'simple' API call\nUnable to build series.\nAlternative method might be added in the future."), MessageBox.TYPE_INFO, timeout=10)
                return streamlist

            lines = seriessimpleresult.splitlines()

            if pythonVer == 3:
                lines = [x for x in lines if "/series/" in x.decode() or "/S01/" in x.decode() or "/E01" in x.decode() and "/live" not in x.decode() and "/movie/" not in x.decode()]
            else:
                lines = [x for x in lines if "/series/" in x or "/S01/" in x or "/E01" in x and "/live" not in x and "/movie/" not in x]

            buildlist = [x for x in seriesstreamresult if str(x["category_id"]) not in glob.current_playlist["data"]["series_categories_hidden"] and
                         str(x["series_id"]) not in glob.current_playlist["data"]["series_streams_hidden"]]

            print("**** length lines ***", len(lines))

            if buildlist:
                print("**** true ***")

                try:
                    x = 0
                    for line in lines:
                        if pythonVer == 3:
                            line = line.decode()

                        if x > 1000:
                            break

                        series_url = line.split(" ")[0]
                        series_name = line.split(":")[-1].strip()
                        series_name = series_name.replace(":", "").replace('"', "").strip("-")
                        series_stream_id = series_url.split("/")[-1].split(".")[0]

                        name = ""

                        for channel in buildlist:
                            if channel['name'] in series_name:
                                name = channel["name"]
                                name = name.replace(":", "").replace('"', "").strip("-")
                                break

                        if name:
                            bouquet_id1 = 0
                            calc_remainder = int(series_stream_id) // 65535
                            bouquet_id1 = bouquet_id1 + calc_remainder
                            bouquet_id2 = int(series_stream_id) - int(calc_remainder * 65535)

                            custom_sid = ":0:1:" + str(format(bouquet_id1, "04x")) + ":" + str(format(bouquet_id2, "04x")) + ":1:" + str(format(self.unique_ref, "08x")) + ":0:0:0:"
                            bouquetString = ""
                            bouquetString += "#SERVICE " + str(self.streamtype) + str(custom_sid) + quote(series_url) + ":" + str(series_name) + "\n"
                            bouquetString += "#DESCRIPTION " + str(series_name) + "\n"
                            streamlist.append({"category_id": str(channel["category_id"]), "stream_id": str(series_stream_id), "bouquetString": bouquetString, "name": str(channel["name"]), "added": str(channel["last_modified"])})
                            x += 1

                    return streamlist
                except Exception as e:
                    print(e)

        else:
            # print("*** no simple api call ***")
            return streamlist

    def build_bouquet_tv_file(self, streamtype, bouquetTitle):
        print("*** build_bouquet_tv ***")
        if cfg.groups.value is True:

            groupname = "userbouquet.bouquetmakerxtream_" + str(self.safefilename) + ".tv"

            with open("/etc/enigma2/bouquets.tv", "r") as f:
                content = f.read()

            with open("/etc/enigma2/bouquets.tv", "a+") as f:
                bouquetTvString = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(groupname) + '" ORDER BY bouquet\n'
                if str(bouquetTvString) not in content:
                    f.write(str(bouquetTvString))

            filename = "/etc/enigma2/" + str(groupname)

            with open(filename, "a+") as f:
                nameString = "#NAME " + str(glob.current_playlist["playlist_info"]["name"]) + "\n"
                f.write(str(nameString))

                filename = "subbouquet.bouquetmakerxtream_" + str(streamtype) + "_" + str(bouquetTitle) + ".tv"
                bouquetTvString = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(filename) + '" ORDER BY bouquet\n'
                f.write(str(bouquetTvString))
        else:
            filename = "userbouquet.bouquetmakerxtream_" + str(streamtype) + "_" + str(bouquetTitle) + ".tv"

            with open("/etc/enigma2/bouquets.tv", "a+") as f:
                bouquetTvString = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "' + str(filename) + '" ORDER BY bouquet\n'
                f.write(str(bouquetTvString))

    def build_userbouquets(self, streamtype, bouquetTitle, bouquetString):
        print("*** build userbouquets ***")
        filepath = "/etc/enigma2/"

        if cfg.groups.value is True:
            cleanGroup = re.sub(r'[\<\>\:\"\/\\\|\?\*]', "_", glob.name)
            cleanGroup = re.sub(r" ", "_", cleanGroup)
            cleanGroup = re.sub(r"_+", "_", cleanGroup)
            filename = "subbouquet.bouquetmakerxtream_" + str(streamtype) + "_" + str(bouquetTitle) + ".tv"
        else:
            filename = "userbouquet.bouquetmakerxtream_" + str(streamtype) + "_" + str(bouquetTitle) + ".tv"
        fullpath = os.path.join(filepath, filename)

        with open(fullpath, "w+") as f:
            f.write(bouquetString)

    def build_xmltv_source(self):
        print("*** build_xmltv_source ***")

        import xml.etree.ElementTree as ET

        safeName = self.safefilename
        filepath = "/etc/epgimport/"
        epgfilename = "bouquetmakerxtream." + str(safeName) + ".channels.xml"
        channelpath = os.path.join(filepath, epgfilename)
        sourcefile = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if not os.path.isfile(sourcefile) or os.stat(sourcefile).st_size == 0:
            with open(sourcefile, "w") as f:
                xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
                xml_str += '<sources>\n'
                xml_str += '<sourcecat sourcecatname="BouquetMakerXtream EPG">\n'
                xml_str += '</sourcecat>\n'
                xml_str += '</sources>\n'
                f.write(xml_str)

        tree = ET.parse(sourcefile)
        root = tree.getroot()
        sourcecat = root.find("sourcecat")

        exists = False

        for sourceitem in sourcecat:
            if channelpath in sourceitem.attrib["channels"]:
                exists = True
                break

        if exists is False:
            source = ET.SubElement(sourcecat, "source", type="gen_xmltv", nocheck="1", channels=channelpath)
            description = ET.SubElement(source, "description")
            description.text = str(safeName)

            url = ET.SubElement(source, "url")
            url.text = str(self.xmltv_api)

            tree.write(sourcefile)

        try:
            with open(sourcefile, "r+") as f:
                xml_str = f.read()
                f.seek(0)
                doc = minidom.parseString(xml_str)
                xml_output = doc.toprettyxml(encoding="utf-8", indent="\t")
                try:
                    xml_output = os.linesep.join([s for s in xml_output.splitlines() if s.strip()])
                except:
                    xml_output = os.linesep.join([s for s in xml_output.decode().splitlines() if s.strip()])
                f.write(xml_output)
        except Exception as e:
            print(e)

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

        self.nextjob(_("Building EPG channel file..."), self.build_xmltv_channels)

    def build_xmltv_channels(self):
        print("*** build_xmltv channels ***")
        safeName = self.safefilename

        filepath = "/etc/epgimport/"
        epgfilename = "bouquetmakerxtream." + str(safeName) + ".channels.xml"
        channelpath = os.path.join(filepath, epgfilename)

        if not os.path.isfile(channelpath):
            open(channelpath, "a").close()

        with open(channelpath, "w") as f:
            xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
            xml_str += '<channels>\n'

            if self.livestreamdata:
                for stream in self.livestreamdata:
                    if stream["xml_str"] and stream["xml_str"] is not None:
                        xml_str += stream["xml_str"]

            xml_str += '</channels>\n'
            f.write(xml_str)

        self.progressvalue += 1
        self["progress"].setValue(self.progressvalue)

    def finished(self):
        print("**** self finished ***")
        self.refresh_bouquets()
        self.getPlaylistUserFile()
        self.session.openWithCallback(self.close, MessageBox, str(self.totalcount) + _(" IPTV Bouquets Created"), MessageBox.TYPE_INFO, timeout=30)

    def getPlaylistUserFile(self):
        self.playlists_all = bmxfunctions.getPlaylistJson()

        with open(playlists_json, "r") as f:
            try:
                self.playlists_all = json.load(f)
            except:
                os.remove(playlists_json)

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == glob.current_playlist["playlist_info"]["full_url"]:
                    self.playlists_all[x]["playlist_info"]["bouquet"] = True
                    break
                x += 1

        self.writeJsonFile()

    def writeJsonFile(self):
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
