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
from .plugin import cfg, common_path, hasConcurrent, hasMultiprocessing, hdr, playlist_file, playlists_json, skin_directory, version


try:
    from http.client import HTTPConnection

    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection

    HTTPConnection.debuglevel = 0

epgimporter = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    epgimporter = True


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

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "playlists.xml")
        with open(skin, "r") as f:
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
            "green": self.openBouquetSettings,
            "cancel": self.quit,
            "ok": self.openBouquetSettings,
            "blue": self.openUserInfo,
            "info": self.openUserInfo,
            "yellow": self.deleteServer,
        }, -2)

        self.timer = eTimer()
        self.playlists_all = []
        self.url_list = []

        self.onLayoutFinish.append(self.__layoutFinished)

    def __layoutFinished(self):
        self.setTitle(self.setup_title)
        self.start()

    def start(self):
        # print("*** start ***")
        self["version"].setText(version)

        if epgimporter:
            self.epgimportCleanup()

        # check if playlists.json file exists in specified location
        self.playlists_all = bmx.getPlaylistJson()

        if self.playlists_all:
            self.playlists_all.sort(key=lambda e: e["playlist_info"]["index"], reverse=False)
            self.delayedDownload()
        else:
            self.close()

        self.clearCaches()

    def epgimportCleanup(self):
        # print("*** epgimportCleanup ***")

        channel_file_list = []
        old_channel_files = pythonglob.glob("/etc/epgimport/bouquetmakerxtream.*.channels.xml")

        self.playlists_all = bmx.getPlaylistJson()

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

    def delayedDownload(self):
        # print("*** delayedDownload ***")
        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.self.makeUrlList()
        self.timer.start(50, True)

    def clearCaches(self):
        try:
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def makeUrlList(self):
        # print("*** makeUrlList ***")
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
            self.processDownloads()
        else:
            self.createSetup()

    def downloadUrl(self, url):
        # print("*** downloadUrl ***")
        index = url[1]
        r = ""
        retries = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""
        try:
            r = http.get(url[0], headers=hdr, timeout=10, verify=False)
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

    def processDownloads(self):
        # print("*** processDownloads ***")
        results = []

        threads = min(len(self.url_list), 10)

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(self.downloadUrl, self.url_list)
                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                try:
                    from multiprocessing.pool import ThreadPool

                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(self.downloadUrl, self.url_list)
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
                result = self.downloadUrl(url)
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

        self.buildPlaylistList()

    def buildPlaylistList(self):
        # print("*** buildPlaylistList ***")
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
                        except:
                            try:
                                time_now_datestamp = datetime.strptime(str(playlists["server_info"]["time_now"]), "%Y-%m-%d %H-%M-%S")
                            except:
                                time_now_datestamp = datetime.strptime(str(playlists["server_info"]["time_now"]), "%Y-%m-%d-%H:%M:%S")

                        playlists["data"]["server_offset"] = datetime.now().hour - time_now_datestamp.hour

                if "auth" in playlists:
                    try:
                        auth = int(playlists["user_info"]["auth"])
                    except:
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
                    except:
                        playlists["playlist_info"]["output"] = "ts"

            if "available_channels" in playlists:
                del playlists["available_channels"]

        self.writeJsonFile()

    def writeJsonFile(self):
        # print("*** writeJsonFile ***")
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
        self.createSetup()

    def createSetup(self):
        # print("*** createSetup ***")
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
                                except:
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
        self.draw_list = [self.buildListEntry(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10]) for x in self.list]
        self["playlists"].setList(self.draw_list)

        if len(self.list) == 1 and cfg.skip_playlists_screen.getValue() is True and playlist["playlist_info"]["valid"] is True:
            self.openBouquetSettings()

    def buildListEntry(self, index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlist_type):
        # print("*** buildListEntry ***")
        if status == (_("Active")) or status == (_("Url OK")) or status == "":
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_green.png"))

            try:
                if int(activenum) >= int(maxnum) and int(maxnum) != 0:
                    pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_yellow.png"))
            except:
                pass

        if status == (_("Banned")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))
        if status == (_("Expired")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_grey.png"))
        if status == (_("Disabled")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_grey.png"))
        if status == (_("Server Not Responding")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))
        if status == (_("Not Authorised")):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))

        return (index, str(name), str(url), str(expires), str(status), pixmap, str(active), str(activenum), str(maxc), str(maxnum), str(fullurl), str(playlist_type))

    def quit(self):
        self.close()

    def deleteServer(self, answer=None):
        # print("*** deleteServer ***")
        if self.list != []:
            self.current_playlist = glob.current_playlist.copy()

            if answer is None:
                self.session.openWithCallback(self.deleteServer, MessageBox, _("Delete selected playlist?"))
            elif answer:
                if glob.current_playlist["playlist_info"]["playlist_type"] != "local":
                    with open(playlist_file, "r+") as f:
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

                self.writeJsonFile()

    def deleteEpgData(self, data=None):
        # print("*** deleteEpgData ***")
        if data is None:
            self.session.openWithCallback(self.deleteEpgData, MessageBox, _("Delete providers EPG data?"))
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
            glob.current_selection = self["playlists"].getIndex()
            glob.current_playlist = self.playlists_all[glob.current_selection]
        else:
            glob.current_selection = 0
            glob.current_playlist = []

    def openUserInfo(self):
        from . import serverinfo

        if self.list != []:
            if "user_info" in glob.current_playlist:
                if "auth" in glob.current_playlist["user_info"] and glob.current_playlist["user_info"]["auth"] == 1:
                    self.session.open(serverinfo.BmxUserInfo)
            else:
                if glob.current_playlist["playlist_info"]["playlist_type"] == "xtream" and glob.current_playlist["playlist_info"]["valid"] is False:
                    self.session.open(MessageBox, _("Url is invalid or playlist/user no longer authorised!"), MessageBox.TYPE_ERROR, timeout=5)

                if glob.current_playlist["playlist_info"]["playlist_type"] != "xtream":
                    self.session.open(MessageBox, _("User Info only available for xtream/XUI One lines"), MessageBox.TYPE_ERROR, timeout=5)

    def openBouquetSettings(self):
        from . import bouquetsettings

        if glob.current_playlist and glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if "user_info" in glob.current_playlist:
                if "auth" in glob.current_playlist["user_info"] and glob.current_playlist["user_info"]["auth"] == 1 and glob.current_playlist["user_info"]["status"] == "Active":
                    self.session.openWithCallback(self.exit, bouquetsettings.BmxBouquetSettings)
                    self.checkOnePlaylist()
            else:
                return
        else:
            if glob.current_playlist["playlist_info"]["valid"]:
                self.session.openWithCallback(self.exit, bouquetsettings.BmxBouquetSettings)
                self.checkOnePlaylist()
            else:
                return

    def checkOnePlaylist(self):
        # print("*** checkOnePlaylist ***")
        if len(self.list) == 1 and cfg.skip_playlists_screen.getValue() is True:
            self.quit()

    def exit(self, answer=None):
        if glob.finished and cfg.auto_close.getValue() is True:
            self.close(True)
