#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from . import parsem3u as parsem3u
from .bmxStaticText import StaticText
from .plugin import cfg, epgimporter, hasConcurrent, hasMultiprocessing, playlist_file, playlists_json, skin_directory, debugs, pythonVer, dir_tmp

import json
import os

from Components.ActionMap import ActionMap
from Components.config import ConfigEnableDisable, ConfigSelection, ConfigSelectionNumber, ConfigText, ConfigYesNo, NoSave, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from enigma import eTimer, ePoint
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

try:
    from urlparse import parse_qs, urlparse
except:
    from urllib.parse import parse_qs, urlparse


class BmxBouquetSettings(ConfigListScreen, Screen):
    def __init__(self, session):
        if debugs:
            print("*** init ***")

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

        self["actions"] = ActionMap(["BMXActions"], {
            "cancel": self.cancel,
            "red": self.cancel,
            "green": self.save,
        }, -2)

        self.hide_live = False
        self.hide_vod = False
        self.hide_series = False

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            player_api = glob.current_playlist["playlist_info"]["player_api"]
            self.p_live_categories_url = str(player_api) + "&action=get_live_categories"
            self.p_vod_categories_url = str(player_api) + "&action=get_vod_categories"
            self.p_series_categories_url = str(player_api) + "&action=get_series_categories"

        self.playlists_all = bmx.getPlaylistJson()

        self.onFirstExecBegin.append(self.start)
        self.onLayoutFinish.append(self.__layoutFinished)

    def clearCaches(self):
        if debugs:
            print("*** clearcaches ***")
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
        if debugs:
            print("*** start ***")

        self.timer = eTimer()

        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(10, True)

    def makeUrlList(self):
        if debugs:
            print("*** makeurllist ***")
        self.url_list = []

        if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                self.url_list.append([self.p_live_categories_url, 0, "json"])
                self.url_list.append([self.p_vod_categories_url, 1, "json"])
                self.url_list.append([self.p_series_categories_url, 2, "json"])
                self.processDownloads("json")

            elif glob.current_playlist["playlist_info"]["playlist_type"] == "external":
                self.url_list.append([glob.current_playlist["playlist_info"]["full_url"], 6, "text"])
                self.processDownloads("text")
        else:
            self.parseM3u8Playlist()

        self.checkCategories()

    def processDownloads(self, outputtype=None):
        if debugs:
            print("*** processdownloads ***")
        results = ""
        threads = min(len(self.url_list), 10)
        if outputtype == "json":
            output_file = ""
        else:
            output_file = os.path.join(dir_tmp, "temp_playlist.m3u")

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        if outputtype == "json":

                            results = executor.map(bmx.downloadUrlCategory, self.url_list)
                        else:
                            results = executor.map(lambda url: bmx.downloadUrlMulti(url, output_file), self.url_list)

                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    from multiprocessing.pool import ThreadPool

                    pool = ThreadPool(threads)
                    if outputtype == "json":
                        results = pool.imap_unordered(bmx.downloadUrlCategory, self.url_list)
                    else:

                        results = pool.imap_unordered(lambda url: bmx.downloadUrlMulti(url, output_file), self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print(e)

            for url, result in zip(self.url_list, results):
                if result:
                    category = result[0]

                    if output_file and os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            response = f.read()
                    else:
                        response = result[1]

                    if response:
                        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                            if category == 0:
                                glob.current_playlist["data"]["live_categories"] = response
                            elif category == 1:
                                glob.current_playlist["data"]["vod_categories"] = response
                            elif category == 2:
                                glob.current_playlist["data"]["series_categories"] = response
                        else:
                            self.parseM3u8Playlist(response)

        else:
            for url in self.url_list:

                if outputtype == "json":
                    result = bmx.downloadUrlCategory(url)
                else:
                    result = bmx.downloadUrlMulti(url, output_file)

                category = result[0]
                response = ""

                if output_file and os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        response = f.read()
                else:
                    response = result[1]

                if response:
                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        if category == 0:
                            glob.current_playlist["data"]["live_categories"] = response
                        elif category == 1:
                            glob.current_playlist["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.current_playlist["data"]["series_categories"] = response
                    else:
                        self.parseM3u8Playlist(response)

                # Delete the file after processing
                if os.path.exists(output_file):
                    os.remove(output_file)

    def parseM3u8Playlist(self, response=None):
        if debugs:
            print("*** parseM3u8Playlist ***")
        self.live_streams, self.vod_streams, self.series_streams = parsem3u.parseM3u8Playlist(response)
        self.makeM3u8CategoriesJson()

    def makeM3u8CategoriesJson(self):
        if debugs:
            print("*** makeM3u8CategoriesJson ***")
        parsem3u.makeM3u8CategoriesJson(self.live_streams, self.vod_streams, self.series_streams)
        self.makeM3u8StreamsJson()

    def makeM3u8StreamsJson(self):
        if debugs:
            print("*** makeM3u8StreamsJson ***")
        parsem3u.makeM3u8StreamsJson(self.live_streams, self.vod_streams, self.series_streams)

    def checkCategories(self):
        if debugs:
            print("*** checkCategories ***")
        if not glob.current_playlist["data"]["live_categories"]:
            self.hide_live = True
            glob.current_playlist["settings"]["show_live"] = False

        if not glob.current_playlist["data"]["vod_categories"]:
            self.hide_vod = True
            glob.current_playlist["settings"]["show_vod"] = False

        if not glob.current_playlist["data"]["series_categories"]:
            self.hide_series = True
            glob.current_playlist["settings"]["show_series"] = False

        self.initConfig()

    def initConfig(self):
        if debugs:
            print("*** initConfig ***")
        live_stream_type_choices = [("1", "DVB(1)"), ("4097", "IPTV(4097)")]
        vod_stream_type_choices = [("4097", "IPTV(4097)")]

        if os.path.exists("/usr/bin/gstplayer"):
            live_stream_type_choices.append(("5001", "GStreamer(5001)"))
            vod_stream_type_choices.append(("5001", "GStreamer(5001)"))

        if os.path.exists("/usr/bin/exteplayer3"):
            live_stream_type_choices.append(("5002", "ExtePlayer(5002)"))
            vod_stream_type_choices.append(("5002", "ExtePlayer(5002)"))

        if os.path.exists("/usr/bin/apt-get"):
            live_stream_type_choices.append(("8193", "DreamOS GStreamer(8193)"))
            vod_stream_type_choices.append(("8193", "DreamOS GStreamer(8193)"))

        iptvname = str(glob.current_playlist["playlist_info"]["name"])
        glob.old_name = iptvname
        prefix_name = glob.current_playlist["settings"]["prefix_name"]
        live_type = str(glob.current_playlist["settings"]["live_type"])
        vod_type = str(glob.current_playlist["settings"]["vod_type"])
        show_live = glob.current_playlist["settings"]["show_live"]
        show_vod = glob.current_playlist["settings"]["show_vod"]
        show_series = glob.current_playlist["settings"]["show_series"]
        live_category_order = glob.current_playlist["settings"]["live_category_order"]
        live_stream_order = glob.current_playlist["settings"]["live_stream_order"]
        vod_category_order = glob.current_playlist["settings"]["vod_category_order"]
        vod_stream_order = glob.current_playlist["settings"]["vod_stream_order"]
        show_superscript = glob.current_playlist["settings"]["show_superscript"]

        self.iptvname_cfg = NoSave(ConfigText(default=iptvname, fixed_size=False))
        self.prefix_name_cfg = NoSave(ConfigYesNo(default=prefix_name))

        self.live_type_cfg = NoSave(ConfigSelection(default=live_type, choices=live_stream_type_choices))
        self.vod_type_cfg = NoSave(ConfigSelection(default=vod_type, choices=vod_stream_type_choices))

        self.show_live_cfg = NoSave(ConfigYesNo(default=show_live))
        self.show_vod_cfg = NoSave(ConfigYesNo(default=show_vod))
        self.show_series_cfg = NoSave(ConfigYesNo(default=show_series))

        self.live_category_order_cfg = NoSave(ConfigSelection(default=live_category_order, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z"))]))
        self.live_stream_order_cfg = NoSave(ConfigSelection(default=live_stream_order, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z")), ("added", _("Newest"))]))
        self.vod_category_order_cfg = NoSave(ConfigSelection(default=vod_category_order, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z"))]))
        self.vod_stream_order_cfg = NoSave(ConfigSelection(default=vod_stream_order, choices=[("original", _("Original Order")), ("alphabetical", _("A-Z")), ("added", _("Newest"))]))

        self.show_superscript_cfg = NoSave(ConfigYesNo(default=show_superscript))

        # self.catchup_shift_cfg = NoSave(ConfigSelectionNumber(min=-9, max=9, stepwidth=1, default=0, wraparound=True))
        # self.fix_epg_cfg = NoSave(ConfigYesNo(default=glob.fixepg)

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            next_days = glob.current_playlist["settings"]["next_days"]
            output = str(glob.current_playlist["playlist_info"]["output"])
            epg_offset = glob.current_playlist["settings"]["epg_offset"]
            epg_alternative = glob.current_playlist["settings"]["epg_alternative"]
            epg_alternative_url = glob.current_playlist["settings"]["epg_alternative_url"]

            self.output_cfg = NoSave(ConfigSelection(default=output, choices=[("ts", "ts"), ("m3u8", "m3u8")]))
            self.epg_offset_cfg = NoSave(ConfigSelectionNumber(-9, 9, 1, default=epg_offset, wraparound=True))
            self.epg_alternative_cfg = NoSave(ConfigYesNo(default=epg_alternative))
            self.epg_alternative_url_cfg = NoSave(ConfigText(default=epg_alternative_url, fixed_size=False))
            self.next_days_cfg = NoSave(ConfigSelection(default=next_days, choices=[("0", _("Default")), ("1", "1"),  ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7")]))

        self.createSetup()

    def createSetup(self):
        if debugs:
            print("*** createSetup ***")
        self.list = []
        self.list.append(getConfigListEntry(_("Short name or provider name:"), self.iptvname_cfg))
        self.list.append(getConfigListEntry(_("Use name as bouquet prefix"), self.prefix_name_cfg))

        if not self.hide_live:
            self.list.append(getConfigListEntry(_("Show LIVE category if available:"), self.show_live_cfg))
            if self.show_live_cfg.value:
                self.list.append(getConfigListEntry(_("Stream Type LIVE:"), self.live_type_cfg))

            if self.show_live_cfg.value:
                self.list.append(getConfigListEntry(_("LIVE category bouquet order"), self.live_category_order_cfg))
                self.list.append(getConfigListEntry(_("LIVE stream bouquet order"), self.live_stream_order_cfg))

        if not self.hide_vod:
            self.list.append(getConfigListEntry(_("Show VOD category if available:"), self.show_vod_cfg))

        if not self.hide_series:
            self.list.append(getConfigListEntry(_("Show SERIES category if available:"), self.show_series_cfg))

        if not self.hide_vod or not self.hide_series:
            if self.show_vod_cfg.value or self.show_series_cfg.value:
                self.list.append(getConfigListEntry(_("Stream Type VOD/SERIES:"), self.vod_type_cfg))
                self.list.append(getConfigListEntry(_("VOD/SERIES category bouquet order"), self.vod_category_order_cfg))
                self.list.append(getConfigListEntry(_("VOD/SERIES streams bouquet order"), self.vod_stream_order_cfg))

        if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream" and self.show_live_cfg.value:
            self.list.append(getConfigListEntry(_("Output:"), self.output_cfg))

            if self.show_live_cfg.value and epgimporter:
                self.list.append(getConfigListEntry(_("Max EPG days to download: (Use Default if EPG events is 0)"), self.next_days_cfg))
                self.list.append(getConfigListEntry(_("EPG offset:"), self.epg_offset_cfg))
                self.list.append(getConfigListEntry(_("Use alternative EPG url:"), self.epg_alternative_cfg))
                if self.epg_alternative_cfg.value:
                    self.list.append(getConfigListEntry(_("Alternative EPG url:"), self.epg_alternative_url_cfg))

        if pythonVer == 3:
            self.list.append(getConfigListEntry(_("Convert superscript characters to normal text:"), self.show_superscript_cfg))

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        self.handleInputHelpers()

    def handleInputHelpers(self):
        if debugs:
            print("*** handleInputHelpers ***")
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
        if debugs:
            print("*** changedEntry ***")
        self.item = self["config"].getCurrent()
        for x in self.onChangedEntry:
            x()

        try:
            if isinstance(self["config"].getCurrent()[1], ConfigEnableDisable) or isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
                self.createSetup()
        except:
            pass

    def getCurrentEntry(self):
        if debugs:
            print("*** getCurrentEntry ***")
        return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

    def getCurrentValue(self):
        if debugs:
            print("*** getCurrentValue ****")
        return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

    def save(self):
        if debugs:
            print("*** save ***")
        if self.list:

            self["config"].instance.moveSelectionTo(1)  # hack to hide texthelper

            if not self.show_live_cfg.value and not self.show_vod_cfg.value and not self.show_series_cfg.value:
                self.session.open(MessageBox, _("No bouquets selected."), MessageBox.TYPE_ERROR, timeout=5)
                self.createSetup()
                return

            # Check name is not blank
            iptvname = self.iptvname_cfg.value.strip()

            if iptvname is None or len(iptvname) < 3:
                self.session.open(MessageBox, _("Bouquet name cannot be blank. Please enter a unique bouquet name. Minimum 3 characters."), MessageBox.TYPE_ERROR, timeout=10)
                return

            # Check if the name already exists
            self.full_url = glob.current_playlist["playlist_info"]["full_url"]

            if self.playlists_all:
                if any(playlists["playlist_info"]["name"] == iptvname and playlists["playlist_info"]["full_url"] != self.full_url for playlists in self.playlists_all):
                    self.session.open(MessageBox, _("Name already used. Please enter a unique name."), MessageBox.TYPE_ERROR, timeout=10)
                    return

            # Initialize variables

            domain = ""
            protocol = ""
            port = ""
            username = ""
            password = ""
            host = ""

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                username = glob.current_playlist["playlist_info"]["username"]
                password = glob.current_playlist["playlist_info"]["password"]

            if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
                protocol = glob.current_playlist["playlist_info"]["protocol"]
                domain = glob.current_playlist["playlist_info"]["domain"]
                port = glob.current_playlist["playlist_info"]["port"]

                if port:
                    host = "%s%s:%s" % (protocol, domain, port)
                else:
                    host = "%s%s" % (protocol, domain)

            # Update playlist settings
            show_live = self.show_live_cfg.value
            show_vod = self.show_vod_cfg.value
            show_series = self.show_series_cfg.value
            live_type = self.live_type_cfg.value
            vod_type = self.vod_type_cfg.value
            live_category_order = self.live_category_order_cfg.value
            vod_category_order = self.vod_category_order_cfg.value
            live_stream_order = self.live_stream_order_cfg.value
            vod_stream_order = self.vod_stream_order_cfg.value
            prefix_name = self.prefix_name_cfg.value
            show_superscript = self.show_superscript_cfg.value

            glob.current_playlist["playlist_info"]["name"] = iptvname
            glob.current_playlist["settings"]["prefix_name"] = prefix_name
            glob.current_playlist["settings"]["show_live"] = show_live
            glob.current_playlist["settings"]["show_vod"] = show_vod
            glob.current_playlist["settings"]["show_series"] = show_series
            glob.current_playlist["settings"]["live_type"] = live_type
            glob.current_playlist["settings"]["vod_type"] = vod_type
            glob.current_playlist["settings"]["live_category_order"] = live_category_order
            glob.current_playlist["settings"]["vod_category_order"] = vod_category_order
            glob.current_playlist["settings"]["live_stream_order"] = live_stream_order
            glob.current_playlist["settings"]["vod_stream_order"] = vod_stream_order
            glob.current_playlist["settings"]["show_superscript"] = show_superscript

            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                media_type = "m3u_plus"
                output = self.output_cfg.value
                if output == "m3u8" and live_type == "1":
                    live_type = "4097"
                epg_offset = int(self.epg_offset_cfg.value)
                epg_alternative = self.epg_alternative_cfg.value
                epg_alternative_url = self.epg_alternative_url_cfg.value
                next_days = self.next_days_cfg.value

                glob.current_playlist["playlist_info"]["output"] = output
                glob.current_playlist["settings"]["epg_offset"] = epg_offset
                glob.current_playlist["settings"]["epg_alternative"] = epg_alternative
                glob.current_playlist["settings"]["epg_alternative_url"] = epg_alternative_url
                glob.current_playlist["settings"]["next_days"] = next_days

                self.full_url = "%s/get.php?username=%s&password=%s&type=%s&output=%s" % (host, username, password, media_type, output)

                glob.current_playlist["playlist_info"]["full_url"] = self.full_url

                if epg_alternative and epg_alternative_url:
                    glob.current_playlist["playlist_info"]["xmltv_api"] = epg_alternative_url

            if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
                # Update playlists.txt file
                if not os.path.isfile(playlist_file):
                    with open(playlist_file, "w+") as f:
                        f.close()

                with open(playlist_file, "r+") as f:
                    lines = f.readlines()
                    f.seek(0)
                    f.truncate()
                    for line in lines:
                        if line.startswith("http"):
                            has_timeshift = False

                            if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream" and "get.php" in line:
                                if domain in line and username in line and password in line:

                                    query = parse_qs(urlparse(line).query, keep_blank_values=True)

                                    has_timeshift = "timeshift" in query

                                    playlist_line = "%s/get.php?username=%s&password=%s&type=%s&output=%s" % (host, username, password, media_type, output)

                                    if has_timeshift or int(epg_offset) != 0:
                                        playlist_line += "&timeshift=%s" % epg_offset

                                    playlist_line += " #%s" % iptvname

                                    line = str(playlist_line) + "\n"

                            else:
                                if self.full_url in line:
                                    line = "%s #%s\n" % (self.full_url, iptvname)
                            f.write(line)
                        else:
                            f.write(line)

            self.getPlaylistUserFile()

    def getPlaylistUserFile(self):
        if debugs:
            print("*** getPlaylistUserFile ***")
        if self.playlists_all:
            for idx, playlists in enumerate(self.playlists_all):
                if playlists["playlist_info"]["full_url"] == self.full_url:

                    self.playlists_all[idx]["playlist_info"]["name"] = glob.current_playlist["playlist_info"]["name"]
                    self.playlists_all[idx]["settings"]["prefix_name"] = glob.current_playlist["settings"]["prefix_name"]
                    self.playlists_all[idx]["settings"]["show_live"] = glob.current_playlist["settings"]["show_live"]
                    self.playlists_all[idx]["settings"]["show_vod"] = glob.current_playlist["settings"]["show_vod"]
                    self.playlists_all[idx]["settings"]["show_series"] = glob.current_playlist["settings"]["show_series"]
                    self.playlists_all[idx]["settings"]["live_type"] = glob.current_playlist["settings"]["live_type"]
                    self.playlists_all[idx]["settings"]["vod_type"] = glob.current_playlist["settings"]["vod_type"]
                    self.playlists_all[idx]["settings"]["live_category_order"] = glob.current_playlist["settings"]["live_category_order"]
                    self.playlists_all[idx]["settings"]["vod_category_order"] = glob.current_playlist["settings"]["vod_category_order"]
                    self.playlists_all[idx]["settings"]["live_stream_order"] = glob.current_playlist["settings"]["live_stream_order"]
                    self.playlists_all[idx]["settings"]["vod_stream_order"] = glob.current_playlist["settings"]["vod_stream_order"]
                    self.playlists_all[idx]["settings"]["show_superscript"] = glob.current_playlist["settings"]["show_superscript"]

                    if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[idx]["playlist_info"]["output"] = glob.current_playlist["playlist_info"]["output"]
                        self.playlists_all[idx]["settings"]["epg_offset"] = glob.current_playlist["settings"]["epg_offset"]
                        self.playlists_all[idx]["settings"]["epg_alternative"] = glob.current_playlist["settings"]["epg_alternative"]
                        self.playlists_all[idx]["settings"]["epg_alternative_url"] = glob.current_playlist["settings"]["epg_alternative_url"]
                        self.playlists_all[idx]["settings"]["next_days"] = glob.current_playlist["settings"]["next_days"]
                        self.playlists_all[idx]["playlist_info"]["full_url"] = glob.current_playlist["playlist_info"]["full_url"]

                    break  # Exit loop after updating

        self.writeJsonFile()

    def writeJsonFile(self):
        if debugs:
            print("*** writeJsonFile ***")
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
        self.clearCaches()

        from . import choosecategories

        self.session.openWithCallback(self.exit, choosecategories.BmxChooseCategories)

    def exit(self, answer=None):
        if debugs:
            print("*** exit ***")
        if glob.finished:
            self.clearCaches()
            self.clearSeries()
            self.close(True)

    def clearSeries(self):
        if debugs:
            print("*** clearSeries ***")
        playlists_all = bmx.getPlaylistJson()

        if playlists_all:
            for playlist in playlists_all:
                playlist["data"]["live_streams"] = []
                playlist["data"]["vod_streams"] = []
                playlist["data"]["series_streams"] = []

            with open(playlists_json, "w") as f:
                json.dump(playlists_all, f)
