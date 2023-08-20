#!/usr/bin/python
# -*- coding: utf-8 -*-


from . import _
from . import bouquet_globals as glob
from . import globalfunctions as bmxfunctions
from .plugin import skin_directory, playlists_json, hdr, playlist_file, cfg, common_path, version, hasConcurrent, hasMultiprocessing
from .bouquetStaticText import StaticText


from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from datetime import datetime
from enigma import eTimer

from requests.adapters import HTTPAdapter, Retry
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap


import json
import glob as pythonglob
import os
import re
import requests
import shutil

try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0
requests.packages.urllib3.disable_warnings()

epgimporter = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    epgimporter = True


class BouquetMakerXtream_Playlists(Screen):
    ALLOW_SUSPEND = True

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "playlists.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = (_("Select Playlist"))

        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("OK"))
        self["key_yellow"] = StaticText(_("Delete"))
        self["key_blue"] = StaticText(_("Info"))
        self["version"] = StaticText()

        self.list = []
        self.drawList = []
        self["playlists"] = List(self.drawList, enableWrapAround=True)
        self["playlists"].onSelectionChanged.append(self.getCurrentEntry)
        self["splash"] = Pixmap()
        self["splash"].show()

        self["actions"] = ActionMap(["BouquetMakerXtreamActions"], {
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
            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except:
            pass

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def start(self):
        self["version"].setText(version)

        if epgimporter:
            self.epgimportcleanup()

        self.playlists_all = []

        # check if playlists.json file exists in specified location
        self.playlists_all = bmxfunctions.getPlaylistJson()

        if self.playlists_all and os.path.isfile(playlist_file) and os.stat(playlist_file).st_size > 0:
            self.playlists_all.sort(key=lambda e: e["playlist_info"]["index"], reverse=False)
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
                self.self.makeUrlList()
        self.timer.start(5, True)

    def makeUrlList(self):
        self.url_list = []
        x = 0
        for playlists in self.playlists_all:
            if playlists["playlist_info"]["playlisttype"] == "xtream":
                player_api = str(playlists["playlist_info"]["player_api"])
                full_url = str(playlists["playlist_info"]["full_url"])
                domain = str(playlists["playlist_info"]["domain"])
                username = str(playlists["playlist_info"]["username"])
                password = str(playlists["playlist_info"]["password"])
                if "get.php" in full_url and domain != "" and username != "" and password != "":
                    self.url_list.append([player_api, x])
                    x += 1

            elif playlists["playlist_info"]["playlisttype"] == "external":
                full_url = str(playlists["playlist_info"]["full_url"])
                self.url_list.append([full_url, x])
                x += 1

        if self.url_list:
            self.process_downloads()

        self.buildPlaylistList()

    def download_url(self, url):
        index = url[1]
        r = ""
        retries = Retry(total=2, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        response = ""
        try:
            r = http.get(url[0], headers=hdr, timeout=5, verify=False)
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
        threads = len(self.url_list)
        if threads > 10:
            threads = 10

        if hasConcurrent or hasMultiprocessing:
            if hasConcurrent:
                print("******* trying concurrent futures ******")
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    executor = ThreadPoolExecutor(max_workers=threads)

                    with executor:
                        results = executor.map(self.download_url, self.url_list)
                except Exception as e:
                    print(e)

            elif hasMultiprocessing:
                print("********** trying multiprocessing threadpool *******")
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
                    # print("*** index ***", index)
                    # print("*** response ***", response)
                    if self.playlists_all[index]["playlist_info"]["playlisttype"] == "xtream":
                        self.playlists_all[index].update(response)
                    self.playlists_all[index]["playlist_info"]["valid"] = True
                else:
                    if self.playlists_all[index]["playlist_info"]["playlisttype"] == "xtream":
                        self.playlists_all[index]["user_info"] = []
                    self.playlists_all[index]["playlist_info"]["valid"] = False

        else:
            print("********** trying sequential download *******")
            for url in self.url_list:
                result = self.download_url(url)
                index = result[0]
                response = result[1]
                if response:
                    if self.playlists_all[index]["playlist_info"]["playlisttype"] == "xtream":
                        self.playlists_all[index].update(response)
                    self.playlists_all[index]["playlist_info"]["valid"] = True
                else:
                    if self.playlists_all[index]["playlist_info"]["playlisttype"] == "xtream":
                        self.playlists_all[index]["user_info"] = []
                    self.playlists_all[index]["playlist_info"]["valid"] = False

        self.buildPlaylistList()

    def buildPlaylistList(self):
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

                        playlists["data"]["serveroffset"] = datetime.now().hour - time_now_datestamp.hour

                if "auth" in playlists:
                    try:
                        auth = int(playlists["user_info"]["auth"])
                    except:
                        playlists["user_info"]["auth"] = 1

                if "status" in playlists["user_info"]:
                    if playlists["user_info"]["status"] != "Active" and playlists["user_info"]["status"] != "Banned" and playlists["user_info"]["status"] != "Disabled" and playlists["user_info"]["status"] != "Expired":
                        playlists["user_info"]["status"] = "Active"

                if "active_cons" in playlists["user_info"]:
                    if not playlists["user_info"]["active_cons"]:
                        playlists["user_info"]["active_cons"] = 0

                if "max_connections" in playlists["user_info"]:
                    if not playlists["user_info"]["max_connections"]:
                        playlists["user_info"]["max_connections"] = 0

                if 'allowed_output_formats' in playlists['user_info']:
                    if playlists["playlist_info"]["output"] not in playlists['user_info']['allowed_output_formats']:
                        try:
                            playlists["playlist_info"]["output"] = str(playlists['user_info']['allowed_output_formats'][0])
                        except:
                            playlists["playlist_info"]["output"] = "ts"

            if "available_channels" in playlists:
                del playlists["available_channels"]

        self.writeJsonFile()

    def writeJsonFile(self):
        with open(playlists_json, "w") as f:
            json.dump(self.playlists_all, f)
        self.createSetup()

    def createSetup(self):
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
            status = (_("Server Not Responding"))
            expires = ""
            fullurl = ""
            playlisttype = ""

            if playlist:
                if "name" in playlist["playlist_info"]:
                    name = playlist["playlist_info"]["name"]
                elif "domain" in playlist["playlist_info"]:
                    name = playlist["playlist_info"]["domain"]

                if "host" in playlist["playlist_info"]:
                    url = playlist["playlist_info"]["host"]

                if "full_url" in playlist["playlist_info"]:
                    fullurl = playlist["playlist_info"]["full_url"]

                if "playlisttype" in playlist["playlist_info"]:
                    playlisttype = playlist["playlist_info"]["playlisttype"]

                if playlist["playlist_info"]["playlisttype"] == "xtream":
                    if "user_info" in playlist and "auth" in playlist["user_info"]:
                        status = (_("Not Authorised"))

                        if playlist["user_info"]["auth"] == 1:

                            if playlist["user_info"]["status"] == "Active":
                                status = (_("Active"))
                            elif playlist["user_info"]["status"] == "Banned":
                                status = (_("Banned"))
                            elif playlist["user_info"]["status"] == "Disabled":
                                status = (_("Disabled"))
                            elif playlist["user_info"]["status"] == "Expired":
                                status = (_("Expired"))

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

                        if playlist["playlist_info"]["playlisttype"] == "external":
                            status = (_("Url OK"))
                            expires = (_("External playlist"))
                        if playlist["playlist_info"]["playlisttype"] == "local":
                            status = ""
                            expires = (_("Local file"))

                self.list.append([index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlisttype])
                index += 1

        self.drawList = []
        self.drawList = [self.buildListEntry(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10]) for x in self.list]
        self["playlists"].setList(self.drawList)

        if len(self.list) == 1 and cfg.skipplaylistsscreen.getValue() is True and playlist["playlist_info"]["valid"] is True:
            self.openBouquetSettings()

    def buildListEntry(self, index, name, url, expires, status, active, activenum, maxc, maxnum, fullurl, playlisttype):
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

        return (index, str(name), str(url), str(expires), str(status), pixmap, str(active), str(activenum), str(maxc), str(maxnum), str(fullurl), str(playlisttype))

    def quit(self):
        self.close()

    def deleteServer(self, answer=None):
        if self.list != []:
            self.currentplaylist = glob.current_playlist.copy()

            if answer is None:
                self.session.openWithCallback(self.deleteServer, MessageBox, _("Delete selected playlist?"))
            elif answer:

                if glob.current_playlist["playlist_info"]["playlisttype"] != "local":
                    with open(playlist_file, "r+") as f:
                        lines = f.readlines()
                        f.seek(0)
                        for line in lines:

                            if str(self.currentplaylist["playlist_info"]["full_url"]) in line:
                                line = "#%s" % line
                            f.write(line)
                else:
                    filename = str(self.currentplaylist["playlist_info"]["full_url"])
                    os.rename(os.path.join(cfg.locallocation.value, filename), os.path.join(cfg.locallocation.value, filename + ".del"))

                x = 0
                for playlist in self.playlists_all:
                    if playlist == self.currentplaylist:
                        del self.playlists_all[x]
                        break
                    x += 1

                """
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
                    self.deleteEpgData()
                    """

                self.writeJsonFile()

    def deleteEpgData(self, data=None):
        if data is None:
            self.session.openWithCallback(self.deleteEpgData, MessageBox, _("Delete providers EPG data?"))
        else:
            # self["splash"].show()
            epglocation = str(cfg.epglocation.value)
            epgfolder = os.path.join(epglocation,  str(self.currentplaylist["playlist_info"]["name"]))

            try:
                shutil.rmtree(epgfolder)
            except:
                pass
            # self["splash"].show()
            # self.start()

    def getCurrentEntry(self):
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
                if "auth" in glob.current_playlist["user_info"]:
                    if glob.current_playlist["user_info"]["auth"] == 1:
                        self.session.open(serverinfo.BouquetMakerXtream_UserInfo)
            else:
                if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream" and glob.current_playlist["playlist_info"]["valid"] is False:
                    self.session.open(MessageBox, _("Url is invalid or playlist/user no longer authorised!"), MessageBox.TYPE_ERROR, timeout=5)

                if glob.current_playlist["playlist_info"]["playlisttype"] != "xtream":
                    self.session.open(MessageBox, _("User Info only available for xtream/XUI One lines"), MessageBox.TYPE_ERROR, timeout=5)

    def openBouquetSettings(self):
        from . import bouquetsettings

        if glob.current_playlist["playlist_info"]["playlisttype"] == "xtream":
            if "user_info" in glob.current_playlist:
                if "auth" in glob.current_playlist["user_info"]:
                    if glob.current_playlist["user_info"]["auth"] == 1 and glob.current_playlist["user_info"]["status"] == "Active":
                        self.session.open(bouquetsettings.BouquetMakerXtream_BouquetSettings)
                        self.checkoneplaylist()
            else:
                return
        else:
            if glob.current_playlist["playlist_info"]["valid"]:
                self.session.open(bouquetsettings.BouquetMakerXtream_BouquetSettings)
                self.checkoneplaylist()
            else:
                return

    def checkoneplaylist(self):
        if len(self.list) == 1 and cfg.skipplaylistsscreen.getValue() is True:
            self.quit()

    def epgimportcleanup(self):
        # print("*** epgimportcleanup ***")

        channelfilelist = []
        oldchannelfiles = pythonglob.glob("/etc/epgimport/bouquetmakerxtream.*.channels.xml")

        self.playlists_all = bmxfunctions.getPlaylistJson()

        for playlist in self.playlists_all:
            cleanName = re.sub(r'[\<\>\:\"\/\\\|\?\*]', "_", str(playlist["playlist_info"]["name"]))
            cleanName = re.sub(r" ", "_", cleanName)
            cleanName = re.sub(r"_+", "_", cleanName)
            channelfilelist.append(cleanName)

        # delete old xmltv channel files
        for filePath in oldchannelfiles:
            exists = False
            for cfile in channelfilelist:
                if cfile in filePath:
                    exists = True

            if exists is False:
                try:
                    os.remove(filePath)
                except:
                    print("Error while deleting file : ", filePath)

        # remove sources from source file
        sourcefile = "/etc/epgimport/bouquetmakerxtream.sources.xml"

        if os.path.isfile(sourcefile):

            import xml.etree.ElementTree as ET
            tree = ET.parse(sourcefile)
            root = tree.getroot()

            for elem in root.iter():
                for child in list(elem):
                    exists = False
                    description = ""
                    if child.tag == "source":
                        try:
                            description = child.find("description").text
                            for cfile in channelfilelist:
                                if cfile in description:
                                    exists = True
                        except:
                            pass

                        if exists is False:
                            elem.remove(child)

            tree.write(sourcefile)
