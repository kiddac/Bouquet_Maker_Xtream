#!/usr/bin/python
# -*- coding: utf-8 -*-

# Standard library imports
from __future__ import division

import json
import glob as pythonglob
import os
import re
from datetime import datetime

try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except ImportError:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0

# Third-party imports
import requests
from requests.adapters import HTTPAdapter, Retry

# Enigma2 components
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

# Local application/library-specific imports
from . import _
from . import bouquet_globals as glob
from .plugin import cfg, common_path, hasConcurrent, hasMultiprocessing, playlist_file, playlists_json, skin_directory, version, epgimporter
from .bmxStaticText import StaticText
from . import checkinternet

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Accept-Encoding': 'gzip, deflate'
}


class BmxPlaylists(Screen):
    ALLOW_SUSPEND = True

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.value)
        skin = os.path.join(skin_path, "playlists.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Select Playlist")

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["key_yellow"] = StaticText(_("Delete"))
        self["key_blue"] = StaticText(_("Info"))
        self["version"] = StaticText()

        self.list = []
        self.drawList = []
        glob.current_playlist = []

        self["playlists"] = List(self.drawList, enableWrapAround=True)
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

        self.onFirstExecBegin.append(self.start)
        self.onLayoutFinish.append(self.__layoutFinished)

    def clear_caches(self):
        try:
            with open("/proc/sys/vm/drop_caches", "w") as drop_caches:
                drop_caches.write("1\n2\n3\n")
        except IOError:
            pass

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def start(self):
        self.checkinternet = checkinternet.check_internet()
        if not self.checkinternet:
            self.session.openWithCallback(self.quit, MessageBox, _("No internet."), type=MessageBox.TYPE_ERROR, timeout=5)
        self["version"].setText(version)

        if epgimporter:
            self.epgimportcleanup()

        self.playlists_all = []

        # check if playlists.json file exists in specified location
        if os.path.isfile(playlists_json):
            with open(playlists_json, "r") as f:
                try:
                    self.playlists_all = json.load(f)
                    self.playlists_all.sort(key=lambda e: e["playlist_info"]["index"], reverse=False)
                except:
                    os.remove(playlists_json)

        if self.playlists_all and os.path.isfile(playlist_file) and os.path.getsize(playlist_file) > 0:
            self.delayedDownload()
        else:
            self.close()

        self.clear_caches()

    def delayedDownload(self):
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.makeUrlList)
        except:
            try:
                self.timer.callback.append(self.makeUrlList)
            except:
                self.makeUrlList()
        self.timer.start(50, True)

    def makeUrlList(self):
        self.url_list = []
        for index, playlists in enumerate(self.playlists_all):
            if playlists["playlist_info"]["playlist_type"] == "xtream":
                player_api = str(playlists["playlist_info"]["player_api"])
                full_url = str(playlists["playlist_info"]["full_url"])
                domain = str(playlists["playlist_info"]["domain"])
                username = str(playlists["playlist_info"]["username"])
                password = str(playlists["playlist_info"]["password"])
                if "get.php" in full_url and domain and username and password:
                    self.url_list.append([player_api, index])

            elif playlists["playlist_info"]["playlist_type"] == "external":
                full_url = str(playlists["playlist_info"]["full_url"])
                self.url_list.append([full_url, index])

        if self.url_list:
            self.process_downloads()
        else:
            self.createSetup()

    def download_url(self, url):
        index = url[1]
        response = None
        retries = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)

        with requests.Session() as http:
            http.mount("http://", adapter)
            http.mount("https://", adapter)

            try:
                # Perform the initial request
                r = http.get(url[0], headers=hdr, timeout=6, verify=False)
                r.raise_for_status()

                if r.status_code == requests.codes.ok:
                    if "player_api.php" in url[0]:
                        try:
                            response = r.json()
                        except Exception as e:
                            print("JSON parsing error:", e)
                    else:
                        try:
                            response = r.text
                            if "EXTM3U" not in response:
                                response = None
                        except Exception as e:
                            print("Text response error:", e)

            except Exception as e:
                print("Request error:", e)

        return index, response

    def process_downloads(self):
        threads = min(len(self.url_list), 5)

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                # print("******* trying concurrent futures ******")
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=threads) as executor:
                        results = list(executor.map(self.download_url, self.url_list))
                except Exception as e:
                    print("Concurrent execution error:", e)

            elif hasMultiprocessing:
                # print("********** trying multiprocessing threadpool *******")
                try:
                    from multiprocessing.pool import ThreadPool
                    pool = ThreadPool(threads)
                    results = pool.imap_unordered(self.download_url, self.url_list)
                    pool.close()
                    pool.join()
                except Exception as e:
                    print("Multiprocessing execution error:", e)

            for index, response in results:
                if response:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index].update(response)
                    self.playlists_all[index]["playlist_info"]["valid"] = True
                else:
                    if self.playlists_all[index]["playlist_info"]["playlist_type"] == "xtream":
                        self.playlists_all[index]["user_info"] = {}
                    self.playlists_all[index]["playlist_info"]["valid"] = False

        else:
            # print("********** trying sequential download *******")
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

        self.buildPlaylistList()

    def buildPlaylistList(self):
        for playlists in self.playlists_all:
            if "user_info" in playlists:
                user_info = playlists["user_info"]

                if "server_info" in playlists:
                    server_info = playlists["server_info"]

                    if "https_port" in server_info:
                        del server_info["https_port"]

                    if "rtmp_port" in server_info:
                        del server_info["rtmp_port"]

                    if "time_now" in server_info:
                        time_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H-%M-%S", "%Y-%m-%d-%H:%M:%S", "%Y- %m-%d %H:%M:%S"]

                        for time_format in time_formats:
                            try:
                                time_now_datestamp = datetime.strptime(str(server_info["time_now"]), time_format)
                                offset = datetime.now().hour - time_now_datestamp.hour
                                # print("*** offset ***", offset)
                                playlists["data"]["server_offset"] = offset
                                break
                            except ValueError:
                                pass

                if "message" in user_info:
                    del user_info["message"]

                auth = user_info.get("auth", 1)
                if not isinstance(auth, int):
                    user_info["auth"] = 1

                if "status" in user_info:
                    valid_statuses = {"Active", "Banned", "Disabled", "Expired"}
                    if user_info["status"] not in valid_statuses:
                        user_info["status"] = "Active"

                if "active_cons" in user_info and not user_info["active_cons"]:
                    user_info["active_cons"] = 0

                if "max_connections" in user_info and not user_info["max_connections"]:
                    user_info["max_connections"] = 0

                if 'allowed_output_formats' in user_info:
                    allowed_formats = user_info['allowed_output_formats'] or []
                    output_format = playlists["playlist_info"]["output"]

                    if output_format not in allowed_formats:
                        playlists["playlist_info"]["output"] = str(allowed_formats[0]) if allowed_formats else "ts"

            if "available_channels" in playlists:
                del playlists["available_channels"]

        self.writeJsonFile()

    def writeJsonFile(self):
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f, indent=4)
        self.createSetup()

    def createSetup(self):
        self["splash"].hide()
        self.list = []
        index = 0

        for index, playlist in enumerate(self.playlists_all):
            status = _("Server Not Responding")

            active = 0
            activenum = 0
            maxc = 0
            maxnum = 0
            expires = ""
            fullurl = ""
            playlist_type = ""

            if playlist:
                name = playlist.get("playlist_info", {}).get("name", playlist.get("playlist_info", {}).get("domain", ""))

                url = playlist.get("playlist_info", {}).get("host", "")

                if "host" in playlist.get("playlist_info", {}):
                    url = playlist.get("playlist_info", {}).get("host", "")

                if "full_url" in playlist.get("playlist_info", {}):
                    fullurl = playlist.get("playlist_info", {}).get("full_url", "")

                if "playlist_type" in playlist.get("playlist_info", {}):
                    playlist_type = playlist.get("playlist_info", {}).get("playlist_type", "")

                if playlist.get("playlist_info", {}).get("playlist_type") == "xtream":

                    if playlist.get("user_info") and "auth" in playlist.get("user_info", {}):
                        status = _("Not Authorised")

                        if str(playlist.get("user_info", {}).get("auth", "")) == "1":

                            usr_status = playlist.get("user_info", {}).get("status", "")

                            if usr_status == "Active":
                                status = _("Active")
                            elif usr_status == "Banned":
                                status = _("Banned")
                            elif usr_status == "Disabled":
                                status = _("Disabled")
                            elif usr_status == "Expired":
                                status = _("Expired")

                            if status == _("Active"):

                                try:
                                    expires = str(_("Expires: ")) + str(
                                        datetime.fromtimestamp(
                                            int(playlist.get("user_info", {}).get("exp_date"))
                                        ).strftime("%d-%m-%Y")
                                    )
                                except:
                                    expires = str(_("Expires: ")) + "Null"

                                active = str(_("Active Conn:"))
                                activenum = playlist.get("user_info", {}).get("active_cons", 0)
                                try:
                                    activenum = int(activenum)
                                except:
                                    activenum = 0

                                maxc = str(_("Max Conn:"))
                                maxnum = playlist.get("user_info", {}).get("max_connections", 0)
                                try:
                                    maxnum = int(maxnum)
                                except:
                                    maxnum = 0

                else:

                    if playlist.get("playlist_info", {}).get("valid"):

                        active = ""
                        activenum = ""
                        maxc = ""
                        maxnum = ""

                        if playlist.get("playlist_info", {}).get("playlist_type") == "external":
                            status = _("Url OK")
                            expires = _("External playlist")

                        if playlist.get("playlist_info", {}).get("playlist_type") == "local":
                            status = ""
                            expires = _("Local file")

            self.list.append([
                index,
                name,
                url,
                expires,
                status,
                active,
                activenum,
                maxc,
                maxnum,
                fullurl,
                playlist_type
            ])

        self.drawList = [
            self.buildListEntry(
                x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10]
            )
            for x in self.list
        ]
        self["playlists"].setList(self.drawList)

        if len(self.list) == 1 and cfg.skip_playlists_screen.getValue() and playlist["playlist_info"]["valid"]:
            self.openBouquetSettings()

    def buildListEntry(self, index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlist_type):
        pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_yellow.png"))

        if status == _("Active") or status == _("Url OK") or status == "":
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_green.png"))

            if activenum == "":
                activenum = 0

            if maxnum == "":
                maxnum = 0
            try:
                if int(activenum) >= int(maxnum) and int(maxnum) != 0:
                    pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_yellow.png"))
            except:
                pass

        if status == _("Banned"):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))
        elif status == _("Expired"):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_grey.png"))
        elif status == _("Disabled"):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_grey.png"))
        elif status == _("Server Not Responding"):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))
        elif status == _("Not Authorised"):
            pixmap = LoadPixmap(cached=True, path=os.path.join(common_path, "led_red.png"))

        return (index, str(name), str(url), str(expires), str(status), pixmap, str(active), str(activenum), str(maxc), str(maxnum), str(fullurl), str(playlist_type))

    def quit(self, answer=None):
        self.close()

    def deleteServer(self, answer=None):
        if not self.list:
            return

        self.current_playlist = glob.current_playlist.copy()

        if answer is None:
            self.session.openWithCallback(self.deleteServer, MessageBox, _("Delete selected playlist?"))
            return

        if answer:
            playlist_type = glob.current_playlist["playlist_info"]["playlist_type"]
            full_url = str(self.current_playlist["playlist_info"]["full_url"])

            if playlist_type != "local":
                with open(playlist_file, "r+") as f:
                    lines = f.readlines()
                    f.seek(0)
                    f.truncate()
                    for line in lines:
                        if str(self.current_playlist["playlist_info"]["full_url"]) in line:
                            line = "#%s" % line
                        f.write(line)
            else:
                filename = full_url
                os.rename(os.path.join(cfg.local_location.value, filename),
                          os.path.join(cfg.local_location.value, filename + ".del"))

            self.playlists_all = [playlist for playlist in self.playlists_all if playlist != self.current_playlist]
            self.writeJsonFile()

            if epgimporter:
                self.epgimportcleanup()

    def getCurrentEntry(self):
        if self.list:
            glob.current_selection = self["playlists"].getIndex()
            glob.current_playlist = self.playlists_all[glob.current_selection]
        else:
            glob.current_selection = 0
            glob.current_playlist = []

    def openUserInfo(self):
        from . import serverinfo

        if not self.list:
            return

        user_info = glob.current_playlist.get("user_info", {})
        playlist_type = glob.current_playlist["playlist_info"]["playlist_type"]

        if "auth" in user_info:
            if user_info["auth"] == 1:
                self.session.open(serverinfo.BmxUserInfo)
                return

            self.session.open(MessageBox, _("Url is invalid or playlist/user no longer authorised!"), MessageBox.TYPE_ERROR, timeout=5)
        elif playlist_type != "xtream":
            self.session.open(MessageBox, _("User Info only available for xtream/XUI One lines"), MessageBox.TYPE_ERROR, timeout=5)

    def openBouquetSettings(self):
        from . import bouquetsettings
        if glob.current_playlist and glob.current_playlist["playlist_info"]["playlist_type"] == "xtream":
            if "user_info" in glob.current_playlist:
                if "auth" in glob.current_playlist["user_info"] and str(glob.current_playlist["user_info"]["auth"]) == "1" and glob.current_playlist["user_info"]["status"] == "Active":
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
        if self.list and len(self.list) == 1 and cfg.skip_playlists_screen.value:
            self.quit()

    def exit(self, answer=None):
        if glob.finished:
            self.close(True)

    def epgimportcleanup(self):
        channelfilelist = []
        oldchannelfiles = pythonglob.glob("/etc/epgimport/bouquetmakerxtream.*.channels.xml")

        try:
            with open(playlists_json, "r") as f:
                self.playlists_all = json.load(f)
        except:
            self.playlists_all = []

        for playlist in self.playlists_all:
            cleanName = re.sub(r'[\'\<\>\:\"\/\\\|\?\*\(\)\[\]]', "_", str(playlist["playlist_info"]["name"]))
            cleanName = re.sub(r" +", "_", cleanName)
            cleanName = re.sub(r"_+", "_", cleanName)
            channelfilelist.append(cleanName)

        for filePath in oldchannelfiles:
            if not any(cfile in filePath for cfile in channelfilelist):
                try:
                    os.remove(filePath)
                except Exception as e:
                    print("Error while deleting file:", filePath, e)
        sourcefile = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if os.path.isfile(sourcefile):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(sourcefile, parser=ET.XMLParser(encoding="utf-8"))
                root = tree.getroot()
                for elem in root.findall(".//source"):
                    description = elem.find("description").text if elem.find("description") is not None else ""
                    if not any(cfile in description for cfile in channelfilelist):
                        if elem in root:
                            root.remove(elem)

                tree.write(sourcefile)
            except Exception as e:
                print("Error:", e)
