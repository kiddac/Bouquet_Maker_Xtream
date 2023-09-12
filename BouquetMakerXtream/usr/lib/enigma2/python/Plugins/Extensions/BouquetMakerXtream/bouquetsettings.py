#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from . import parsem3u as parsem3u
from .plugin import skin_directory, playlist_file, playlists_json, hasConcurrent, hasMultiprocessing, cfg, epgimporter
from .bouquetStaticText import StaticText

from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, ConfigText, ConfigSelection, ConfigYesNo, ConfigEnableDisable, NoSave, ConfigSelectionNumber
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from enigma import eTimer

import os
import json


try:
    from urlparse import urlparse, parse_qs
except:
    from urllib.parse import urlparse, parse_qs


class BouquetMakerXtream_BouquetSettings(ConfigListScreen, Screen):

    def __init__(self, session):
        Screen.__init__(self, session)

        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "settings.xml")

        if os.path.exists("/var/lib/dpkg/status"):
            skin = os.path.join(skin_path, "DreamOS/settings.xml")

        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Bouquets Settings")

        self.onChangedEntry = []

        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Continue"))
        self["information"] = StaticText("")

        self["VKeyIcon"] = Pixmap()
        self["VKeyIcon"].hide()
        self["HelpWindow"] = Pixmap()
        self["HelpWindow"].hide()

        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
            "cancel": self.cancel,
            "red": self.cancel,
            "green": self.save,
        }, -2)

        self.hidelive = False
        self.hidevod = False
        self.hideseries = False

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.player_api = glob.current_playlist["playlist_info"]["player_api"]
            self.p_live_categories_url = str(self.player_api) + "&action=get_live_categories"
            self.p_vod_categories_url = str(self.player_api) + "&action=get_vod_categories"
            self.p_series_categories_url = str(self.player_api) + "&action=get_series_categories"

        self.onFirstExecBegin.append(self.start)
        self.onLayoutFinish.append(self.__layoutFinished)

    def clear_caches(self):
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def cancel(self):
        self.close()

    def start(self):
        # print("*** self start ***")
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(5, True)

    def makeUrlList(self):
        # print("*** makeUrlList ***")
        self.url_list = []

        if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.url_list.append([self.p_live_categories_url, 0, "json"])
                self.url_list.append([self.p_vod_categories_url, 1, "json"])
                self.url_list.append([self.p_series_categories_url, 2, "json"])
            elif glob.current_playlist["playlist_info"]["playlisttype"] == "external":
                self.url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6, "text"])
        else:
            self.parse_m3u8_playlist()

        self.process_downloads()
        self.check_categories()

    def process_downloads(self):
        # print("*** process_downloads ***")

        results = ""

        threads = len(self.url_list)
        if threads > 10:
            threads = 10

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(bmx.download_url_multi, self.url_list)
                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    from multiprocessing.pool import ThreadPool
                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(bmx.download_url_multi, self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print(e)

            for category, response in results:
                if response:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        if category == 0:
                            glob.current_playlist["data"]["live_categories"] = response
                        elif category == 1:
                            glob.current_playlist["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.current_playlist["data"]["series_categories"] = response
                    else:
                        self.parse_m3u8_playlist(response)

        else:
            for url in self.url_list:
                result = bmx.download_url_multi(url)
                category = result[0]
                response = result[1]
                if response:
                    if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                        # add categories to main json file
                        if category == 0:
                            glob.current_playlist["data"]["live_categories"] = response
                        elif category == 1:
                            glob.current_playlist["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.current_playlist["data"]["series_categories"] = response
                    else:
                        self.parse_m3u8_playlist(response)

    def parse_m3u8_playlist(self, response=None):
        # print("*** parse_m3u8_playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parse_m3u8_playlist(response)
        self.make_m3u8_categories_json()

    def make_m3u8_categories_json(self):
        # print("*** make_m3u8_categories_json  ***")
        parsem3u.make_m3u8_categories_json(self.live_streams, self.vod_streams, self.series_streams)
        self.make_m3u8_streams_json()

    def make_m3u8_streams_json(self):
        # print("*** make_m3u8_streams_json  ***")
        parsem3u.make_m3u8_streams_json(self.live_streams, self.vod_streams, self.series_streams)

    def check_categories(self):
        # print("*** check_categories ***")
        if not glob.current_playlist["data"]["live_categories"]:
            self.hidelive = True
            glob.current_playlist["settings"]["showlive"] = False

        if not glob.current_playlist["data"]["vod_categories"]:
            self.hidevod = True
            glob.current_playlist["settings"]["showvod"] = False

        if not glob.current_playlist["data"]["series_categories"]:
            self.hideseries = True
            glob.current_playlist["settings"]["showseries"] = False

        self.initConfig()

    def initConfig(self):
        live_streamtype_choices = [("1", "DVB(1)"), ("4097", "IPTV(4097)")]
        vod_streamtype_choices = [("4097", "IPTV(4097)")]

        if os.path.exists("/usr/bin/gstplayer"):
            live_streamtype_choices.append(("5001", "GStreamer(5001)"))
            vod_streamtype_choices.append(("5001", "GStreamer(5001)"))

        if os.path.exists("/usr/bin/exteplayer3"):
            live_streamtype_choices.append(("5002", "ExtePlayer(5002)"))
            vod_streamtype_choices.append(("5002", "ExtePlayer(5002)"))

        if os.path.exists("/usr/bin/apt-get"):
            live_streamtype_choices.append(("8193", "DreamOS GStreamer(8193)"))
            vod_streamtype_choices.append(("8193", "DreamOS GStreamer(8193)"))

        self.name = str(glob.current_playlist["playlist_info"]["name"])
        self.prefixname = glob.current_playlist["settings"]["prefixname"]
        self.liveType = str(glob.current_playlist["settings"]["livetype"])
        self.vodType = str(glob.current_playlist["settings"]["vodtype"])
        self.showlive = glob.current_playlist["settings"]["showlive"]
        self.showvod = glob.current_playlist["settings"]["showvod"]
        self.showseries = glob.current_playlist["settings"]["showseries"]
        self.livecategoryorder = glob.current_playlist["settings"]["livecategoryorder"]
        self.livestreamorder = glob.current_playlist["settings"]["livestreamorder"]
        self.vodcategoryorder = glob.current_playlist["settings"]["vodcategoryorder"]
        self.vodstreamorder = glob.current_playlist["settings"]["vodstreamorder"]

        self.nameCfg = NoSave(ConfigText(default=self.name, fixed_size=False))
        self.prefixNameCfg = NoSave(ConfigYesNo(default=self.prefixname))

        self.liveTypeCfg = NoSave(ConfigSelection(default=self.liveType, choices=live_streamtype_choices))
        self.vodTypeCfg = NoSave(ConfigSelection(default=self.vodType, choices=vod_streamtype_choices))

        self.showliveCfg = NoSave(ConfigYesNo(default=self.showlive))
        self.showvodCfg = NoSave(ConfigYesNo(default=self.showvod))
        self.showseriesCfg = NoSave(ConfigYesNo(default=self.showseries))

        self.liveCategoryOrderCfg = NoSave(ConfigSelection(default=self.livecategoryorder, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z"))]))
        self.liveStreamOrderCfg = NoSave(ConfigSelection(default=self.livestreamorder, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z")), ("added", _("Newest"))]))
        self.vodCategoryOrderCfg = NoSave(ConfigSelection(default=self.vodcategoryorder, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z"))]))
        self.vodStreamOrderCfg = NoSave(ConfigSelection(default=self.vodstreamorder, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z")), ("added", _("Newest"))]))

        self.catchupShiftCfg = NoSave(ConfigSelectionNumber(min=-9, max=9, stepwidth=1, default=glob.catchupshift, wraparound=True))
        # self.FixEPGCfg = NoSave(ConfigYesNo(default=glob.fixepg)

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.output = str(glob.current_playlist["playlist_info"]["output"])
            self.epgoffset = glob.current_playlist["settings"]["epgoffset"]
            self.epgalternative = glob.current_playlist["settings"]["epgalternative"]
            self.epgalternativeurl = glob.current_playlist["settings"]["epgalternativeurl"]
            self.directsource = glob.current_playlist["settings"]["directsource"]

            self.outputCfg = NoSave(ConfigSelection(default=self.output, choices=[("ts", "ts"), ("m3u8", "m3u8")]))
            self.epgoffsetCfg = NoSave(ConfigSelectionNumber(-9, 9, 1, default=self.epgoffset, wraparound=True))
            self.epgalternativeCfg = NoSave(ConfigYesNo(default=self.epgalternative))
            self.epgalternativeurlCfg = NoSave(ConfigText(default=self.epgalternativeurl, fixed_size=False))
            self.directsourceCfg = NoSave(ConfigSelection(default=self.directsource, choices=[("Standard", "Standard"), ("Direct Source", "Direct Source")]))

        self.createSetup()

    def createSetup(self):
        self.list = []
        self.list.append(getConfigListEntry(_("Short name or provider name:"), self.nameCfg))
        self.list.append(getConfigListEntry(_("Use name as bouquet prefix"), self.prefixNameCfg))

        if self.hidelive is False:
            self.list.append(getConfigListEntry(_("Show LIVE category if available:"), self.showliveCfg))
            if self.showliveCfg.value is True:
                self.list.append(getConfigListEntry(_("Stream Type LIVE:"), self.liveTypeCfg))

            if self.showliveCfg.value is True:
                self.list.append(getConfigListEntry(_("LIVE category bouquet order"), self.liveCategoryOrderCfg))
                self.list.append(getConfigListEntry(_("LIVE stream bouquet order"), self.liveStreamOrderCfg))

        if self.hidevod is False:
            self.list.append(getConfigListEntry(_("Show VOD category if available:"), self.showvodCfg))

        if self.hideseries is False:
            self.list.append(getConfigListEntry(_("Show SERIES category if available:"), self.showseriesCfg))

        if self.hidevod is False or self.hideseries is False:
            if self.showvodCfg.value is True or self.showseriesCfg.value is True:
                self.list.append(getConfigListEntry(_("Stream Type VOD/SERIES:"), self.vodTypeCfg))

            if self.showvodCfg.value is True:
                self.list.append(getConfigListEntry(_("VOD/SERIES category bouquet order"), self.vodCategoryOrderCfg))
                self.list.append(getConfigListEntry(_("VOD/SERIES streams bouquet order"), self.vodStreamOrderCfg))

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            self.list.append(getConfigListEntry(_("Output:"), self.outputCfg))
            self.list.append(getConfigListEntry(_("Stream Source URL:"), self.directsourceCfg))

            if self.showliveCfg.value is True and epgimporter is True:
                self.list.append(getConfigListEntry(_("EPG offset:"), self.epgoffsetCfg))
                self.list.append(getConfigListEntry(_("Use alternative EPG url:"), self.epgalternativeCfg))
                if self.epgalternativeCfg.value is True:
                    self.list.append(getConfigListEntry(_("Alternative EPG url:"), self.epgalternativeurlCfg))

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        self.handleInputHelpers()

    def handleInputHelpers(self):
        from enigma import ePoint
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
            if isinstance(self["config"].getCurrent()[1], ConfigEnableDisable) or isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
                self.createSetup()
        except:
            pass

    def getCurrentEntry(self):
        return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

    def getCurrentValue(self):
        return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

    def save(self):
        if self.list:
            if self.showliveCfg.value is False and self.showvodCfg.value is False and self.showseriesCfg.value is False:
                from Screens.MessageBox import MessageBox
                self.session.open(MessageBox, _("No bouquets selected."), MessageBox.TYPE_ERROR, timeout=5)
                self.createSetup()
                return

            self['config'].instance.moveSelectionTo(1)  # hack to hide texthelper

            if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
                self.protocol = glob.current_playlist["playlist_info"]["protocol"]
                self.domain = glob.current_playlist["playlist_info"]["domain"]
                self.port = glob.current_playlist["playlist_info"]["port"]

                if self.port:
                    self.host = "%s%s:%s" % (self.protocol, self.domain, self.port)
                else:
                    self.host = "%s%s" % (self.protocol, self.domain)

            self.full_url = glob.current_playlist["playlist_info"]["full_url"]

            self.name = self.nameCfg.value.strip()

            showlive = self.showliveCfg.value
            showvod = self.showvodCfg.value
            showseries = self.showseriesCfg.value
            livetype = self.liveTypeCfg.value
            vodtype = self.vodTypeCfg.value
            livecategoryorder = self.liveCategoryOrderCfg.value
            vodcategoryorder = self.vodCategoryOrderCfg.value
            livestreamorder = self.liveStreamOrderCfg.value
            vodstreamorder = self.vodStreamOrderCfg.value
            prefixname = self.prefixNameCfg.value
            glob.current_playlist["playlist_info"]["name"] = self.name
            glob.current_playlist["settings"]["prefixname"] = prefixname
            glob.current_playlist["settings"]["showlive"] = showlive
            glob.current_playlist["settings"]["showvod"] = showvod
            glob.current_playlist["settings"]["showseries"] = showseries
            glob.current_playlist["settings"]["livetype"] = livetype
            glob.current_playlist["settings"]["vodtype"] = vodtype
            glob.current_playlist["settings"]["livecategoryorder"] = livecategoryorder
            glob.current_playlist["settings"]["vodcategoryorder"] = vodcategoryorder
            glob.current_playlist["settings"]["livestreamorder"] = livestreamorder
            glob.current_playlist["settings"]["vodstreamorder"] = vodstreamorder

            if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                self.username = glob.current_playlist["playlist_info"]["username"]
                self.password = glob.current_playlist["playlist_info"]["password"]
                self.listtype = "m3u"
                output = self.outputCfg.value
                if output == "m3u8" and livetype == "1":
                    livetype = "4097"
                epgoffset = int(self.epgoffsetCfg.value)
                epgalternative = self.epgalternativeCfg.value
                epgalternativeurl = self.epgalternativeurlCfg.value
                directsource = self.directsourceCfg.value

                glob.current_playlist["playlist_info"]["output"] = output
                glob.current_playlist["settings"]["epgoffset"] = epgoffset
                glob.current_playlist["settings"]["epgalternative"] = epgalternative
                glob.current_playlist["settings"]["epgalternativeurl"] = epgalternativeurl
                glob.current_playlist["settings"]["directsource"] = directsource

                playlistline = "%s/get.php?username=%s&password=%s&type=%s&output=%s&timeshift=%s #%s" % (self.host, self.username, self.password, self.listtype, output, epgoffset, self.name)
                self.full_url = "%s/get.php?username=%s&password=%s&type=%s&output=%s" % (self.host, self.username, self.password, self.listtype, self.output)

                glob.current_playlist["playlist_info"]["full_url"] = self.full_url
                if epgalternativeurl:
                    glob.current_playlist["playlist_info"]["xmltv_api"] = epgalternativeurl

            if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
                # update playlists.txt file
                if not os.path.isfile(playlist_file):
                    with open(playlist_file, "w+") as f:
                        f.close()

                with open(playlist_file, "r+") as f:
                    lines = f.readlines()
                    f.seek(0)
                    exists = False
                    for line in lines:
                        hastimeshift = False

                        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and "get.php" in line:
                            if self.domain in line and self.username in line and self.password in line:
                                parsed_uri = urlparse(line)
                                protocol = parsed_uri.scheme + "://"
                                domain = parsed_uri.hostname
                                port = ""

                                if parsed_uri.port:
                                    port = parsed_uri.port
                                    host = "%s%s:%s" % (protocol, domain, port)
                                else:
                                    host = "%s%s" % (protocol, domain)

                                query = parse_qs(parsed_uri.query, keep_blank_values=True)

                                if "username" in query:
                                    username = query["username"][0].strip()
                                else:
                                    continue

                                if "password" in query:
                                    password = query["password"][0].strip()
                                else:
                                    continue
                                if "timeshift" in query:
                                    hastimeshift = True

                                if hastimeshift or int(epgoffset) != 0:
                                    playlistline = "%s/get.php?username=%s&password=%s&type=%s&output=%s&timeshift=%s #%s" % (host, username, password, self.listtype, output, epgoffset, self.name)
                                else:
                                    playlistline = "%s/get.php?username=%s&password=%s&type=%s&output=%s #%s" % (host, username, password, self.listtype, output, self.name)

                                line = str(playlistline) + "\n"
                                exists = True
                            f.write(line)

                        else:
                            if self.full_url in line:
                                playlistline = "%s #%s" % (self.full_url, self.name)
                                exists = True
                            f.write(line)

                    if exists is False:
                        f.write("\n" + str(playlistline) + "\n")

            self.getPlaylistUserFile()

    def getPlaylistUserFile(self):
        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == self.full_url:
                    self.playlists_all[x] = glob.current_playlist
                    break
                x += 1

        self.writeJsonFile()

    def writeJsonFile(self):
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
        self.clear_caches()

        from . import choosecategories
        self.session.openWithCallback(self.close, choosecategories.BouquetMakerXtream_ChooseCategories)
