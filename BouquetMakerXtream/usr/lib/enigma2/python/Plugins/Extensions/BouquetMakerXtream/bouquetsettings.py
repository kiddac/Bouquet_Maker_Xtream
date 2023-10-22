#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os

from Components.ActionMap import ActionMap
from Components.config import ConfigEnableDisable, ConfigSelection, ConfigSelectionNumber, ConfigText, ConfigYesNo, NoSave, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from enigma import ePoint, eTimer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from . import parsem3u as parsem3u
from .bmxStaticText import StaticText
from .plugin import cfg, EPGIMPORTER, HAS_CONCURRENT, HAS_MULTIPROCESSING, PLAYLIST_FILE, PLAYLISTS_JSON, SKIN_DIRECTORY, PYTHON_VER

if PYTHON_VER == 2:
    from io import open

try:
    from urlparse import parse_qs, urlparse
except ImportError:
    from urllib.parse import parse_qs, urlparse


class BmxBouquetSettings(ConfigListScreen, Screen):
    def __init__(self, session):
        Screen.__init__(self, session)

        self.session = session

        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "settings.xml")

        if os.path.exists("/var/lib/dpkg/status"):
            skin = os.path.join(skin_path, "DreamOS/settings.xml")

        with open(skin, "r", encoding="utf-8") as f:
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

        self.timer = eTimer()

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            player_api = glob.CURRENT_PLAYLIST["playlist_info"]["player_api"]
            self.p_live_categories_url = str(player_api) + "&action=get_live_categories"
            self.p_vod_categories_url = str(player_api) + "&action=get_vod_categories"
            self.p_series_categories_url = str(player_api) + "&action=get_series_categories"

        self.playlists_all = bmx.get_playlist_json()

        self.onFirstExecBegin.append(self.start)
        self.onLayoutFinish.append(self.__layout_finished)

    def clear_caches(self):
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except Exception:
            pass

    def __layout_finished(self):
        self.setTitle(self.setup_title)

    def cancel(self):
        self.close()

    def start(self):
        # print("*** self start ***")
        try:
            self.timer_conn = self.timer.timeout.connect(self.make_url_list)
        except Exception:
            try:
                self.timer.callback.append(self.make_url_list)
            except Exception:
                self.make_url_list()
        self.timer.start(5, True)

    def make_url_list(self):
        # print("*** make_url_list ***")
        self.url_list = []

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "local":
            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                self.url_list.append([self.p_live_categories_url, 0, "json"])
                self.url_list.append([self.p_vod_categories_url, 1, "json"])
                self.url_list.append([self.p_series_categories_url, 2, "json"])
            elif glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "external":
                self.url_list.append([glob.CURRENT_PLAYLIST["playlist_info"]["full_url"], 6, "text"])
        else:
            self.parse_m3u8_playlist()

        self.process_downloads()
        self.check_categories()

    def process_downloads(self):
        # print("*** process_downloads ***")

        results = ""

        threads = min(len(self.url_list), 10)

        if HAS_CONCURRENT or HAS_MULTIPROCESSING:
            if HAS_CONCURRENT:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(bmx.download_url_multi, self.url_list)
                except Exception as e:
                    print(e)

            elif HAS_MULTIPROCESSING:
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
                    if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                        if category == 0:
                            glob.CURRENT_PLAYLIST["data"]["live_categories"] = response
                        elif category == 1:
                            glob.CURRENT_PLAYLIST["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.CURRENT_PLAYLIST["data"]["series_categories"] = response
                    else:
                        self.parse_m3u8_playlist(response)

        else:
            for url in self.url_list:
                result = bmx.download_url_multi(url)
                category = result[0]
                response = result[1]
                if response:
                    if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                        # add categories to main json file
                        if category == 0:
                            glob.CURRENT_PLAYLIST["data"]["live_categories"] = response
                        elif category == 1:
                            glob.CURRENT_PLAYLIST["data"]["vod_categories"] = response
                        elif category == 2:
                            glob.CURRENT_PLAYLIST["data"]["series_categories"] = response
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
        if not glob.CURRENT_PLAYLIST["data"]["live_categories"]:
            self.hide_live = True
            glob.CURRENT_PLAYLIST["settings"]["show_live"] = False

        if not glob.CURRENT_PLAYLIST["data"]["vod_categories"]:
            self.hide_vod = True
            glob.CURRENT_PLAYLIST["settings"]["show_vod"] = False

        if not glob.CURRENT_PLAYLIST["data"]["series_categories"]:
            self.hide_series = True
            glob.CURRENT_PLAYLIST["settings"]["show_series"] = False

        self.init_config()

    def init_config(self):
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

        self.name = str(glob.CURRENT_PLAYLIST["playlist_info"]["name"])
        glob.OLD_NAME = self.name
        prefix_name = glob.CURRENT_PLAYLIST["settings"]["prefix_name"]
        live_type = str(glob.CURRENT_PLAYLIST["settings"]["live_type"])
        vod_type = str(glob.CURRENT_PLAYLIST["settings"]["vod_type"])
        show_live = glob.CURRENT_PLAYLIST["settings"]["show_live"]
        show_vod = glob.CURRENT_PLAYLIST["settings"]["show_vod"]
        show_series = glob.CURRENT_PLAYLIST["settings"]["show_series"]
        live_category_order = glob.CURRENT_PLAYLIST["settings"]["live_category_order"]
        live_stream_order = glob.CURRENT_PLAYLIST["settings"]["live_stream_order"]
        vod_category_order = glob.CURRENT_PLAYLIST["settings"]["vod_category_order"]
        vod_stream_order = glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"]

        self.name_cfg = NoSave(ConfigText(default=self.name, fixed_size=False))
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

        self.catchup_shift_cfg = NoSave(ConfigSelectionNumber(min=-9, max=9, stepwidth=1, default=glob.CATCHUP_SHIFT, wraparound=True))
        # self.fix_epg_cfg = NoSave(ConfigYesNo(default=glob.FIXEPG)

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            output = str(glob.CURRENT_PLAYLIST["playlist_info"]["output"])
            epg_offset = glob.CURRENT_PLAYLIST["settings"]["epg_offset"]
            epg_alternative = glob.CURRENT_PLAYLIST["settings"]["epg_alternative"]
            epg_alternative_url = glob.CURRENT_PLAYLIST["settings"]["epg_alternative_url"]

            self.output_cfg = NoSave(ConfigSelection(default=output, choices=[("ts", "ts"), ("m3u8", "m3u8")]))
            self.epg_offset_cfg = NoSave(ConfigSelectionNumber(-9, 9, 1, default=epg_offset, wraparound=True))
            self.epg_alternative_cfg = NoSave(ConfigYesNo(default=epg_alternative))
            self.epg_alternative_url_cfg = NoSave(ConfigText(default=epg_alternative_url, fixed_size=False))

        self.create_setup()

    def create_setup(self):
        self.list = []
        self.list.append(getConfigListEntry(_("Short name or provider name:"), self.name_cfg))
        self.list.append(getConfigListEntry(_("Use name as bouquet prefix"), self.prefix_name_cfg))

        if self.hide_live is False:
            self.list.append(getConfigListEntry(_("Show LIVE category if available:"), self.show_live_cfg))
            if self.show_live_cfg.value is True:
                self.list.append(getConfigListEntry(_("Stream Type LIVE:"), self.live_type_cfg))

            if self.show_live_cfg.value is True:
                self.list.append(getConfigListEntry(_("LIVE category bouquet order"), self.live_category_order_cfg))
                self.list.append(getConfigListEntry(_("LIVE stream bouquet order"), self.live_stream_order_cfg))

        if self.hide_vod is False:
            self.list.append(getConfigListEntry(_("Show VOD category if available:"), self.show_vod_cfg))

        if self.hide_series is False:
            self.list.append(getConfigListEntry(_("Show SERIES category if available:"), self.show_series_cfg))

        if self.hide_vod is False or self.hide_series is False:
            if self.show_vod_cfg.value is True or self.show_series_cfg.value is True:
                self.list.append(getConfigListEntry(_("Stream Type VOD/SERIES:"), self.vod_type_cfg))

            if self.show_vod_cfg.value is True:
                self.list.append(getConfigListEntry(_("VOD/SERIES category bouquet order"), self.vod_category_order_cfg))
                self.list.append(getConfigListEntry(_("VOD/SERIES streams bouquet order"), self.vod_stream_order_cfg))

        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            self.list.append(getConfigListEntry(_("Output:"), self.output_cfg))

            if self.show_live_cfg.value is True and EPGIMPORTER is True:
                # self.list.append(getConfigListEntry(_("EPG offset:"), self.epg_offset_cfg))
                self.list.append(getConfigListEntry(_("Use alternative EPG url:"), self.epg_alternative_cfg))
                if self.epg_alternative_cfg.value is True:
                    self.list.append(getConfigListEntry(_("Alternative EPG url:"), self.epg_alternative_url_cfg))

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        self.handle_input_helpers()

    def handle_input_helpers(self):
        curr_config = self["config"].getCurrent()

        if curr_config is not None:
            if isinstance(curr_config[1], ConfigText):
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

                if "HelpWindow" in self and curr_config[1].help_window and curr_config[1].help_window.instance is not None:
                    helpwindowpos = self["HelpWindow"].getPosition()
                    curr_config[1].help_window.instance.move(ePoint(helpwindowpos[0], helpwindowpos[1]))

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
            if isinstance(self["config"].getCurrent()[1], (ConfigEnableDisable, ConfigYesNo, ConfigSelection)):
                self.create_setup()
        except:
            pass

    def getCurrentEntry(self):
        return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

    def getCurrentValue(self):
        return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

    def save(self):
        # print("*** save ***")
        if self.list:
            if self.show_live_cfg.value is False and self.show_vod_cfg.value is False and self.show_series_cfg.value is False:
                self.session.open(MessageBox, _("No bouquets selected."), MessageBox.TYPE_ERROR, timeout=5)
                self.create_setup()
                return

            self["config"].instance.moveSelectionTo(1)  # hack to hide texthelper

            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "local":
                protocol = glob.CURRENT_PLAYLIST["playlist_info"]["protocol"]
                domain = glob.CURRENT_PLAYLIST["playlist_info"]["domain"]
                port = glob.CURRENT_PLAYLIST["playlist_info"]["port"]

                if port:
                    host = "%s%s:%s" % (protocol, domain, port)
                else:
                    host = "%s%s" % (protocol, domain)

            self.full_url = glob.CURRENT_PLAYLIST["playlist_info"]["full_url"]
            self.name = self.name_cfg.value.strip()

            # check name is not blank
            if self.name is None or len(self.name) < 3:
                self.session.open(MessageBox, _("Bouquet name cannot be blank. Please enter a unique bouquet name. Minimum 3 characters."), MessageBox.TYPE_ERROR, timeout=10)
                # self.create_setup()
                return

            # check name exists
            if self.playlists_all:
                for playlists in self.playlists_all:
                    if playlists["playlist_info"]["name"] == self.name and str(playlists["playlist_info"]["full_url"]) != str(self.full_url):
                        self.session.open(MessageBox, _("Name already used. Please enter a unique name."), MessageBox.TYPE_ERROR, timeout=10)
                        # self.create_setup()
                        return

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
            glob.CURRENT_PLAYLIST["playlist_info"]["name"] = self.name
            glob.CURRENT_PLAYLIST["settings"]["prefix_name"] = prefix_name
            glob.CURRENT_PLAYLIST["settings"]["show_live"] = show_live
            glob.CURRENT_PLAYLIST["settings"]["show_vod"] = show_vod
            glob.CURRENT_PLAYLIST["settings"]["show_series"] = show_series
            glob.CURRENT_PLAYLIST["settings"]["live_type"] = live_type
            glob.CURRENT_PLAYLIST["settings"]["vod_type"] = vod_type
            glob.CURRENT_PLAYLIST["settings"]["live_category_order"] = live_category_order
            glob.CURRENT_PLAYLIST["settings"]["vod_category_order"] = vod_category_order
            glob.CURRENT_PLAYLIST["settings"]["live_stream_order"] = live_stream_order
            glob.CURRENT_PLAYLIST["settings"]["vod_stream_order"] = vod_stream_order

            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
                username = glob.CURRENT_PLAYLIST["playlist_info"]["username"]
                password = glob.CURRENT_PLAYLIST["playlist_info"]["password"]
                list_type = "m3u"
                output = self.output_cfg.value
                if output == "m3u8" and live_type == "1":
                    live_type = "4097"
                epg_offset = int(self.epg_offset_cfg.value)
                epg_alternative = self.epg_alternative_cfg.value
                epg_alternative_url = self.epg_alternative_url_cfg.value

                glob.CURRENT_PLAYLIST["playlist_info"]["output"] = output
                glob.CURRENT_PLAYLIST["settings"]["epg_offset"] = epg_offset
                glob.CURRENT_PLAYLIST["settings"]["epg_alternative"] = epg_alternative
                glob.CURRENT_PLAYLIST["settings"]["epg_alternative_url"] = epg_alternative_url

                playlist_line = "%s/get.php?username=%s&password=%s&type=%s&output=%s&timeshift=%s #%s" % (host, username, password, list_type, output, epg_offset, self.name,)
                self.full_url = "%s/get.php?username=%s&password=%s&type=%s&output=%s" % (host, username, password, list_type, output)

                glob.CURRENT_PLAYLIST["playlist_info"]["full_url"] = self.full_url
                if epg_alternative and epg_alternative_url:
                    glob.CURRENT_PLAYLIST["playlist_info"]["xmltv_api"] = epg_alternative_url

            if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "local":
                # update playlists.txt file
                if not os.path.isfile(PLAYLIST_FILE):
                    with open(PLAYLIST_FILE, "w+", encoding="utf-8") as f:
                        f.close()

                with open(PLAYLIST_FILE, "r+", encoding="utf-8") as f:
                    lines = f.readlines()
                    f.seek(0)
                    for line in lines:
                        has_timeshift = False

                        if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream" and "get.php" in line:
                            if domain in line and username in line and password in line:
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
                                    has_timeshift = True

                                if has_timeshift or int(epg_offset) != 0:
                                    playlist_line = "%s/get.php?username=%s&password=%s&type=%s&output=%s&timeshift=%s #%s" % (host, username, password, list_type, output, epg_offset, self.name)
                                else:
                                    playlist_line = "%s/get.php?username=%s&password=%s&type=%s&output=%s #%s" % (host, username, password, list_type, output, self.name)

                                line = str(playlist_line) + "\n"
                        else:
                            if self.full_url in line:
                                playlist_line = "%s #%s" % (self.full_url, self.name)
                                line = str(playlist_line) + "\n"

                        f.write(line)

            self.get_playlist_user_file()

    def get_playlist_user_file(self):
        if self.playlists_all:
            x = 0
            for playlists in self.playlists_all:
                if playlists["playlist_info"]["full_url"] == self.full_url:
                    self.playlists_all[x] = glob.CURRENT_PLAYLIST
                    break
                x += 1

        self.write_json_file()

    def write_json_file(self):
        with open(PLAYLISTS_JSON, "w", encoding="utf-8") as f:
            json.dump(self.playlists_all, f)
        self.clear_caches()

        from . import choosecategories

        self.session.openWithCallback(self.exit, choosecategories.BmxChooseCategories)

    def exit(self, answer=None):
        if glob.FINISHED:
            self.close(True)
