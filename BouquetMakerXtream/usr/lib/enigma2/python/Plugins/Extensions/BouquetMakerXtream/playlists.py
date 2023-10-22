#!/usr/bin/python
# -*- coding: utf-8 -*-

import glob as pythonglob
import json
import os
import re
import shutil
from datetime import datetime

import requests
from Components.ActionMap import ActionMap
from Components.config import config
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from requests.adapters import HTTPAdapter, Retry
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction
from Tools.LoadPixmap import LoadPixmap

from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmx
from .bmxStaticText import StaticText
from .plugin import cfg, COMMON_PATH, HAS_CONCURRENT, HAS_MULTIPROCESSING, HDR, PLAYLIST_FILE, PLAYLISTS_JSON, SKIN_DIRECTORY, VERSION, PYTHON_VER

if PYTHON_VER == 2:
    from io import open

try:
    from http.client import HTTPConnection

    HTTPConnection.debuglevel = 0
except ImportError:
    from httplib import HTTPConnection

    HTTPConnection.debuglevel = 0

EPGIMPORTER = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    EPGIMPORTER = True


class ProtectedScreen:
    def __init__(self):
        if self.is_protected():
            self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pin_entered, PinInput, pinList=[cfg.adultpin.value], triesEntry=cfg.retries.adultpin, title=_("Please enter the correct pin code"), windowTitle=_("Enter pin code")))

    def is_protected(self):
        return config.plugins.BouquetMakerXtream.adult.value

    def pin_entered(self, result):
        if result is None:
            self.close_protected_screen()
        elif not result:
            self.session.openWithCallback(self.close_protected_screen, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)

    def close_protected_screen(self, result=None):
        self.close(None)


class BmxPlaylists(Screen, ProtectedScreen):
    ALLOW_SUSPEND = True

    def __init__(self, session):
        Screen.__init__(self, session)

        if cfg.adult.getValue() is True:
            ProtectedScreen.__init__(self)

        self.session = session

        skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.getValue())
        skin = os.path.join(skin_path, "playlists.xml")
        with open(skin, "r", encoding="utf-8") as f:
            self.skin = f.read()

        self.setup_title = _("Select Playlist")

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["key_yellow"] = StaticText(_("Delete"))
        self["key_blue"] = StaticText(_("Info"))
        self["version"] = StaticText("")

        self.list = []
        self.draw_list = []
        self["playlists"] = List(self.draw_list, enableWrapAround=True)
        self["playlists"].onSelectionChanged.append(self.getCurrentEntry)
        self["splash"] = Pixmap()
        self["splash"].show()

        self["actions"] = ActionMap(["BMXActions"], {
            "red": self.quit,
            "green": self.open_bouquet_settings,
            "cancel": self.quit,
            "ok": self.open_bouquet_settings,
            "blue": self.open_user_info,
            "info": self.open_user_info,
            "yellow": self.delete_server,
        }, -2)

        self.timer = eTimer()
        self.playlists_all = []
        self.url_list = []

        self.onLayoutFinish.append(self.__layout_finished)

    def __layout_finished(self):
        self.setTitle(self.setup_title)
        self.start()

    def start(self):
        # print("*** start ***")
        self["version"].setText(VERSION)

        if EPGIMPORTER:
            self.epgimport_cleanup()

        # check if playlists.json file exists in specified location
        self.playlists_all = bmx.get_playlist_json()

        if self.playlists_all:
            self.playlists_all.sort(key=lambda e: e["playlist_info"]["index"], reverse=False)
            self.delayed_download()
        else:
            self.close()

        self.clear_caches()

    def epgimport_cleanup(self):
        # print("*** epgimport_cleanup ***")

        channel_file_list = []
        old_channel_files = pythonglob.glob("/etc/epgimport/bouquetmakerxtream.*.channels.xml")

        self.playlists_all = bmx.get_playlist_json()

        for playlist in self.playlists_all:
            clean_name = re.sub(r"[\<\>\:\"\/\\\|\?\*]", "_", str(playlist["playlist_info"]["name"]))
            clean_name = re.sub(r" ", "_", clean_name)
            clean_name = re.sub(r"_+", "_", clean_name)
            channel_file_list.append(clean_name)

        # delete old xmltv channel files
        for file_path in old_channel_files:
            exists = False
            for cfile in channel_file_list:
                if cfile in file_path:
                    exists = True

            if exists is False:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print("Error while deleting file : ", file_path)
                    print(e)

        # remove sources from source file
        source_file = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if os.path.isfile(source_file):
            import xml.etree.ElementTree as ET

            tree = ET.parse(source_file)
            root = tree.getroot()
            for elem in root.iter():
                for child in list(elem):
                    exists = False
                    description = ""
                    if child.tag == "source":
                        try:
                            description = child.find("description").text
                            for cfile in channel_file_list:
                                if cfile in description:
                                    exists = True
                        except:
                            pass

                        if exists is False:
                            elem.remove(child)
            tree.write(source_file)

    def delayed_download(self):
        # print("*** delayed_download ***")
        try:
            self.timer_conn = self.timer.timeout.connect(self.make_url_list)
        except Exception:
            try:
                self.timer.callback.append(self.make_url_list)
            except Exception:
                self.self.make_url_list()
        self.timer.start(50, True)

    def clear_caches(self):
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def make_url_list(self):
        # print("*** make_url_list ***")
        x = 0
        for playlists in self.playlists_all:
            if playlists["playlist_info"]["playlist_type"] == "xtream":
                player_api = str(playlists["playlist_info"]["player_api"])
                full_url = str(playlists["playlist_info"]["full_url"])
                domain = str(playlists["playlist_info"]["domain"])
                username = str(playlists["playlist_info"]["username"])
                password = str(playlists["playlist_info"]["password"])
                if "get.php" in full_url and domain != "" and username != "" and password != "":
                    self.url_list.append([player_api, x])
                    x += 1

            elif playlists["playlist_info"]["playlist_type"] == "external":
                full_url = str(playlists["playlist_info"]["full_url"])
                self.url_list.append([full_url, x])
                x += 1

        if self.url_list:
            self.process_downloads()
        else:
            self.create_setup()

    def download_url(self, url):
        # print("*** download_url ***")
        index = url[1]
        r = ""
        retries = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""
        try:
            r = http.get(url[0], headers=HDR, timeout=10, verify=False)
            r.raise_for_status()
            if r.status_code == requests.codes.ok:
                if "player_api.php" in url[0]:
                    try:
                        response = r.json()
                        return index, response
                    except Exception as e:
                        print(e)
                        return index, ""
                else:
                    try:
                        response = r.text

                        if "EXTM3U" in response:
                            return index, response
                        else:
                            return index, ""
                    except Exception as e:
                        print(e)
                        return index, ""

        except Exception as e:
            print(e)

        return index, ""

    def process_downloads(self):
        # print("*** process_downloads ***")
        results = []

        threads = min(len(self.url_list), 10)

        if HAS_CONCURRENT or HAS_MULTIPROCESSING:
            if HAS_CONCURRENT:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(self.download_url, self.url_list)
                except Exception as e:
                    print(e)

            elif HAS_MULTIPROCESSING:
                try:
                    from multiprocessing.pool import ThreadPool

                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(self.download_url, self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print(e)

            for index, response in results:
                if response:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index].update(response)
                    self.playlists_all[index]["playlist_info"]["valid"] = True
                else:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index]["user_info"] = []
                    self.playlists_all[index]["playlist_info"]["valid"] = False

        else:
            for url in self.url_list:
                result = self.download_url(url)
                index = result[0]
                response = result[1]
                if response:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index].update(response)
                    self.playlists_all[index]["playlist_info"]["valid"] = True
                else:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index]["user_info"] = []
                    self.playlists_all[index]["playlist_info"]["valid"] = False

        self.build_playlist_list()

    def build_playlist_list(self):
        # print("*** build_playlist_list ***")
        for playlists in self.playlists_all:
            if "user_info" in playlists:
                if "message" in playlists["user_info"]:
                    del playlists["user_info"]["message"]

                if "server_info" in playlists:
                    if "https_port" in playlists["server_info"]:
                        del playlists["server_info"]["https_port"]

                    if "rtmp_port" in playlists["server_info"]:
                        del playlists["server_info"]["rtmp_port"]

                    if "time_now" in playlists["server_info"]:
                        try:
                            time_now_datestamp = datetime.strptime(str(playlists["server_info"]["time_now"]), "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            try:
                                time_now_datestamp = datetime.strptime(str(playlists["server_info"]["time_now"]), "%Y-%m-%d %H-%M-%S")
                            except Exception:
                                time_now_datestamp = datetime.strptime(str(playlists["server_info"]["time_now"]), "%Y-%m-%d-%H:%M:%S")

                        playlists["data"]["server_offset"] = datetime.now().hour - time_now_datestamp.hour

                if "auth" in playlists:
                    try:
                        auth = int(playlists["user_info"]["auth"])
                    except Exception:
                        playlists["user_info"]["auth"] = 1

                if "status" in playlists["user_info"] and playlists["user_info"]["status"] != "Active" and playlists["user_info"]["status"] != "Banned" and playlists["user_info"]["status"] != "Disabled" and playlists["user_info"]["status"] != "Expired":
                    playlists["user_info"]["status"] = "Active"

                if "active_cons" in playlists["user_info"] and not playlists["user_info"]["active_cons"]:
                    playlists["user_info"]["active_cons"] = 0

                if "max_connections" in playlists["user_info"] and not playlists["user_info"]["max_connections"]:
                    playlists["user_info"]["max_connections"] = 0

                if "allowed_output_formats" in playlists["user_info"] and playlists["playlist_info"]["output"] not in playlists["user_info"]["allowed_output_formats"]:
                    try:
                        playlists["playlist_info"]["output"] = str(playlists["user_info"]["allowed_output_formats"][0])
                    except Exception:
                        playlists["playlist_info"]["output"] = "ts"

            if "available_channels" in playlists:
                del playlists["available_channels"]

        self.write_json_file()

    def write_json_file(self):
        # print("*** write_json_file ***")
        with open(PLAYLISTS_JSON, "w", encoding="utf-8") as f:
            json.dump(self.playlists_all, f)
        self.create_setup()

    def create_setup(self):
        # print("*** create_setup ***")
        try:
            self["splash"].hide()
        except:
            pass

        self.list = []
        index = 0

        for playlist in self.playlists_all:
            name = ""
            url = ""
            active = ""
            activenum = ""
            maxc = ""
            maxnum = ""
            status = _("Server Not Responding")
            expires = ""
            fullurl = ""
            playlist_type = ""

            if playlist:
                if "name" in playlist["playlist_info"]:
                    name = playlist["playlist_info"]["name"]
                elif "domain" in playlist["playlist_info"]:
                    name = playlist["playlist_info"]["domain"]

                if "host" in playlist["playlist_info"]:
                    url = playlist["playlist_info"]["host"]

                if "full_url" in playlist["playlist_info"]:
                    fullurl = playlist["playlist_info"]["full_url"]

                if "playlist_type" in playlist["playlist_info"]:
                    playlist_type = playlist["playlist_info"]["playlist_type"]

                if playlist["playlist_info"]["playlist_type"] == "xtream":
                    if "user_info" in playlist and "auth" in playlist["user_info"]:
                        status = _("Not Authorised")

                        if playlist["user_info"]["auth"] == 1:
                            if playlist["user_info"]["status"] == "Active":
                                status = _("Active")
                            elif playlist["user_info"]["status"] == "Banned":
                                status = _("Banned")
                            elif playlist["user_info"]["status"] == "Disabled":
                                status = _("Disabled")
                            elif playlist["user_info"]["status"] == "Expired":
                                status = _("Expired")

                            if status == (_("Active")):
                                try:
                                    expires = str(_("Expires: ")) + str(datetime.fromtimestamp(int(playlist["user_info"]["exp_date"])).strftime("%d-%m-%Y"))
                                except Exception:
                                    expires = str(_("Expires: ")) + str("Null")

                                active = str(_("Active Conn:"))
                                activenum = playlist["user_info"]["active_cons"]

                                maxc = str(_("Max Conn:"))
                                maxnum = playlist["user_info"]["max_connections"]

                else:
                    if playlist["playlist_info"]["valid"] is True:
                        active = ""
                        activenum = ""
                        maxc = ""
                        maxnum = ""

                        if playlist["playlist_info"]["playlist_type"] == "external":
                            status = _("Url OK")
                            expires = _("External playlist")
                        if playlist["playlist_info"]["playlist_type"] == "local":
                            status = ""
                            expires = _("Local file")

                self.list.append([index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlist_type])
                index += 1

        self.draw_list = []
        self.draw_list = [self.build_list_entry(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10]) for x in self.list]
        self["playlists"].setList(self.draw_list)

        if len(self.list) == 1 and cfg.skip_playlists_screen.getValue() is True and playlist["playlist_info"]["valid"] is True:
            self.open_bouquet_settings()

    def build_list_entry(self, index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlist_type):
        # print("*** build_list_entry ***")
        if status == (_("Active")) or status == (_("Url OK")) or status == "":
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_green.png"))

            try:
                if int(activenum) >= int(maxnum) and int(maxnum) != 0:
                    pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_yellow.png"))
            except:
                pass

        if status == (_("Banned")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_red.png"))
        if status == (_("Expired")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_grey.png"))
        if status == (_("Disabled")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_grey.png"))
        if status == (_("Server Not Responding")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_red.png"))
        if status == (_("Not Authorised")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(COMMON_PATH, "led_red.png"))

        return (index, str(name), str(url), str(expires), str(status), pixmap, str(active), str(activenum), str(maxc), str(maxnum), str(fullurl), str(playlist_type))

    def quit(self):
        self.close()

    def delete_server(self, answer=None):
        # print("*** delete_server ***")
        if self.list != []:
            self.current_playlist = glob.CURRENT_PLAYLIST.copy()

            if answer is None:
                self.session.openWithCallback(self.delete_server, MessageBox, _("Delete selected playlist?"))
            elif answer:
                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "local":
                    with open(PLAYLIST_FILE, "r+", encoding="utf-8") as f:
                        lines = f.readlines()
                        f.seek(0)
                        f.truncate()
                        for line in lines:
                            if str(self.current_playlist["playlist_info"]["full_url"]) in line:
                                line = "#%s" % line
                            f.write(line)
                else:
                    filename = str(self.current_playlist["playlist_info"]["full_url"])
                    os.rename(os.path.join(cfg.local_location.value, filename), os.path.join(cfg.local_location.value, filename + ".del"))

                x = 0
                for playlist in self.playlists_all:
                    if playlist == self.current_playlist:
                        del self.playlists_all[x]
                        break
                    x += 1

                self.write_json_file()

    def delete_epg_data(self, data=None):
        # print("*** delete_epg_data ***")
        if data is None:
            self.session.openWithCallback(self.delete_epg_data, MessageBox, _("Delete providers EPG data?"))
        else:
            epg_location = str(cfg.epg_location.value)
            epg_folder = os.path.join(epg_location, str(self.current_playlist["playlist_info"]["name"]))

            try:
                shutil.rmtree(epg_folder)
            except:
                pass

    def getCurrentEntry(self):
        # print("*** getCurrentEntry ***")
        if self.list != []:
            glob.CURRENT_SELECTION = self["playlists"].getIndex()
            glob.CURRENT_PLAYLIST = self.playlists_all[glob.CURRENT_SELECTION]
        else:
            glob.CURRENT_SELECTION = 0
            glob.CURRENT_PLAYLIST = []

    def open_user_info(self):
        from . import serverinfo

        if self.list != []:
            if "user_info" in glob.CURRENT_PLAYLIST:
                if "auth" in glob.CURRENT_PLAYLIST["user_info"] and glob.CURRENT_PLAYLIST["user_info"]["auth"] == 1:
                    self.session.open(serverinfo.BmxUserInfo)
            else:
                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream" and glob.CURRENT_PLAYLIST["playlist_info"]["valid"] is False:
                    self.session.open(MessageBox, _("Url is invalid or playlist/user no longer authorised!"), MessageBox.TYPE_ERROR, timeout=5)

                if glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] != "xtream":
                    self.session.open(MessageBox, _("User Info only available for xtream/XUI One lines"), MessageBox.TYPE_ERROR, timeout=5)

    def open_bouquet_settings(self):
        from . import bouquetsettings

        if glob.CURRENT_PLAYLIST and glob.CURRENT_PLAYLIST["playlist_info"]["playlist_type"] == "xtream":
            if "user_info" in glob.CURRENT_PLAYLIST:
                if "auth" in glob.CURRENT_PLAYLIST["user_info"] and glob.CURRENT_PLAYLIST["user_info"]["auth"] == 1 and glob.CURRENT_PLAYLIST["user_info"]["status"] == "Active":
                    self.session.openWithCallback(
                        self.exit, bouquetsettings.BmxBouquetSettings
                    )
                    self.check_one_playlist()
            else:
                return
        else:
            if glob.CURRENT_PLAYLIST["playlist_info"]["valid"]:
                self.session.openWithCallback(self.exit, bouquetsettings.BmxBouquetSettings)
                self.check_one_playlist()
            else:
                return

    def check_one_playlist(self):
        # print("*** check_one_playlist ***")
        if len(self.list) == 1 and cfg.skip_playlists_screen.getValue() is True:
            self.quit()

    def exit(self, answer=None):
        if glob.FINISHED and cfg.auto_close.getValue() is True:
            self.close(True)
