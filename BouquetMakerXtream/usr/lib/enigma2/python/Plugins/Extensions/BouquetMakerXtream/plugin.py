#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re
import shutil
import sys
import time
from datetime import datetime

import requests
import twisted.python.runtime
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigClock, ConfigDirectory, ConfigInteger, ConfigPIN, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, config
from enigma import addFont, eServiceReference, eTimer, getDesktop
from Plugins.Plugin import PluginDescriptor
from requests.adapters import HTTPAdapter, Retry
from Screens.ChannelSelection import ChannelSelectionBase
from ServiceReference import ServiceReference

from . import _
from . import bouquet_globals as glob

try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin

try:
    from multiprocessing.pool import ThreadPool

    hasMultiprocessing = True
except:
    hasMultiprocessing = False

try:
    from concurrent.futures import ThreadPoolExecutor
    if twisted.python.runtime.platform.supportsThreads():
        hasConcurrent = True
    else:
        hasConcurrent = False
except:
    hasConcurrent = False

pythonFull = float(str(sys.version_info.major) + "." + str(sys.version_info.minor))
pythonVer = sys.version_info.major

epgimporter = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    epgimporter = True

isDreambox = False
if os.path.exists("/usr/bin/apt-get"):
    isDreambox = True

with open("/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/version.txt", "r") as f:
    version = f.readline()

screenwidth = getDesktop(0).size()

dir_etc = "/etc/enigma2/bouquetmakerxtream/"
dir_plugins = "/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/"

if screenwidth.width() == 2560:
    skin_directory = os.path.join(dir_plugins, "skin/uhd/")
elif screenwidth.width() > 1280:
    skin_directory = os.path.join(dir_plugins, "skin/fhd/")
else:
    skin_directory = os.path.join(dir_plugins, "skin/hd/")

folders = os.listdir(skin_directory)
if "common" in folders:
    folders.remove("common")

config.plugins.BouquetMakerXtream = ConfigSubsection()
cfg = config.plugins.BouquetMakerXtream

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

cfg.live_type = ConfigSelection(default="4097", choices=live_stream_type_choices)
cfg.vod_type = ConfigSelection(default="4097", choices=vod_stream_type_choices)

cfg.location = ConfigDirectory(default=dir_etc)
cfg.local_location = ConfigDirectory(default=dir_etc)
cfg.main = ConfigYesNo(default=True)
cfg.skin = ConfigSelection(default="default", choices=folders)
cfg.parental = ConfigYesNo(default=False)
cfg.timeout = ConfigSelectionNumber(1, 20, 1, default=10, wraparound=True)
cfg.catchup_on = ConfigYesNo(default=False)
cfg.catchup = ConfigYesNo(default=True)
cfg.catchup_prefix = ConfigSelection(default="~", choices=[("~", "~"), ("!", "!"), ("#", "#"), ("-", "-"), ("^", "^")])
cfg.catchup_start = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.catchup_end = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.skip_playlists_screen = ConfigYesNo(default=False)
cfg.wakeup = ConfigClock(default=((9 * 60) + 15) * 60)  # 10:15
cfg.adult = ConfigYesNo(default=False)
cfg.adultpin = ConfigPIN(default=0000)
cfg.retries = ConfigSubsection()
cfg.retries.adultpin = ConfigSubsection()
cfg.retries.adultpin.tries = ConfigInteger(default=3)
cfg.retries.adultpin.time = ConfigInteger(default=3)
cfg.autoupdate = ConfigYesNo(default=False)
cfg.groups = ConfigYesNo(default=False)
cfg.location_valid = ConfigYesNo(default=True)
cfg.position = ConfigSelection(default="bottom", choices=[("bottom", _("Bottom")), ("top", _("Top"))])
cfg.auto_close = ConfigYesNo(default=False)
cfg.picon_location = ConfigSelection(default="/media/hdd/picon/", choices=[("/media/hdd/picon/", "/media/hdd/picon"), ("/media/usb/picon/", "/media/usb/picon"), ("/usr/share/enigma2/picon/", "/usr/share/enigma2/picon")])

skin_path = os.path.join(skin_directory, cfg.skin.value)
common_path = os.path.join(skin_directory, "common/")
playlists_json = os.path.join(dir_etc, "bmx_playlists.json")
playlist_file = os.path.join(dir_etc, "playlists.txt")

location = cfg.location.getValue()
if location:
    if os.path.exists(location):
        playlist_file = os.path.join(cfg.location.value, "playlists.txt")
        cfg.location_valid.setValue(True)
        cfg.save()
    else:
        cfg.location.setValue(dir_etc)
        cfg.location_valid.setValue(False)
        cfg.save()

font_folder = os.path.join(dir_plugins, "fonts/")

hdr = {"User-Agent": "Enigma2 - BouquetMakerXtream Plugin"}

# create folder for working files
if not os.path.exists(dir_etc):
    os.makedirs(dir_etc)

# check if playlists.txt file exists in specified location
if not os.path.isfile(playlist_file):
    open(playlist_file, "a").close()

# check if playlists.json file exists in specified location
if not os.path.isfile(playlists_json):
    open(playlists_json, "a").close()

# remove dodgy versions of my plugin
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/XStreamityPro/"):
    try:
        shutil.rmtree("/usr/lib/enigma2/python/Plugins/Extensions/XStreamityPro/")
    except Exception as e:
        print(e)

# try and override epgimport settings
try:
    config.plugins.epgimport.import_onlybouquet.value = False
    config.plugins.epgimport.import_onlybouquet.save()
except Exception as e:
    print(e)


def main(session, **kwargs):
    from . import mainmenu

    session.open(mainmenu.BmxMainMenu)
    return


def mainmenu(menu_id, **kwargs):
    if menu_id == "mainmenu":
        return [(_("Bouquet Maker Xtream"), main, "BouquetMakerXtream", 49)]
    else:
        return []


def extensionsmenu(session, **kwargs):
    from . import mainmenu

    session.open(mainmenu.BmxMainMenu)


# Global variables
autoStartTimer = None
originalref = None
originalrefstring = None
BmxChannelSelectionBase__init__ = None
_session = None


class AutoStartTimer:
    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.onTimer)
        except:
            self.timer.callback.append(self.onTimer)
        self.update()

    def getWakeTime(self):
        if cfg.autoupdate.value:
            clock = cfg.wakeup.value
            nowt = time.time()
            now = time.localtime(nowt)
            waketime = int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, clock[0], clock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
            return waketime
        else:
            return -1

    def update(self, atLeast=0):
        self.timer.stop()
        wake = self.getWakeTime()
        now_t = time.time()
        now = int(now_t)

        if wake > 0:
            if wake < now + atLeast:
                wake += 24 * 3600  # add 24 hours to next wake time
            next = wake - now
            self.timer.startLongTimer(next)
        else:
            wake = -1

        wdt = datetime.fromtimestamp(wake)
        ndt = datetime.fromtimestamp(now)

        print("[BouquetMakerXtream] WakeUpTime now set to", wdt, "(now=%s)" % ndt)
        return wake

    def onTimer(self):
        self.timer.stop()
        now = int(time.time())
        wake = self.getWakeTime()
        atLeast = 0
        if wake - now < 60:
            self.runUpdate()
            atLeast = 60
        self.update(atLeast)

    def runUpdate(self):
        print("\n *********** BouquetMakerXtream runupdate ************ \n")
        from . import update

        self.session.open(update.BmxUpdate, "auto")


def autostart(reason, session=None, **kwargs):
    # called with reason=1 to during shutdown, with reason=0 at startup?

    if cfg.catchup_on.getValue() is True and session is not None:
        global BmxChannelSelectionBase__init__
        BmxChannelSelectionBase__init__ = ChannelSelectionBase.__init__
        ChannelSelectionBase.__init__ = MyChannelSelectionBase__init__
        ChannelSelectionBase.showBmxCatchup = showBmxCatchup
        ChannelSelectionBase.playOriginalChannel = playOriginalChannel

    global autoStartTimer
    global _session

    now_t = time.time()
    now = int(now_t)
    ndt = datetime.fromtimestamp(now)

    print("[BouquetMakerXtream] autostart (%s) occured at" % reason, ndt)

    if reason == 0 and _session is None:
        if session is not None:
            _session = session
            if autoStartTimer is None:
                autoStartTimer = AutoStartTimer(session)


def MyChannelSelectionBase__init__(self, session):
    BmxChannelSelectionBase__init__(self, session)
    self["BmxCatchupAction"] = HelpableActionMap(self, "BMXCatchupActions", {
        "catchup": self.showBmxCatchup,
    })


def showBmxCatchup(self):
    try:
        global originalref
        global originalrefstring
        originalref = self.session.nav.getCurrentlyPlayingServiceReference()
        originalrefstring = originalref.toString()
    except:
        pass

    selected_ref = self["list"].getCurrent()
    selected_ref_string = selected_ref.toString()

    glob.currentref = ServiceReference(selected_ref)

    path = str(selected_ref.getPath())

    if "http" not in path:
        return

    glob.name = glob.currentref.getServiceName()

    is_catchup_channel = False
    ref_url = ""
    ref_stream = ""
    ref_stream_num = ""
    username = ""
    password = ""
    domain = ""

    original_path = ServiceReference(originalref).getPath()
    ref_url = glob.currentref.getPath()

    # http://domain.xyx:0000/live/user/pass/12345.ts

    if "/live/" not in ref_url:
        return

    ref_stream = ref_url.split("/")[-1]
    # 12345.ts

    ref_stream_num = int(ref_stream.split(".")[0])
    # 12345

    # get domain, username, password from path
    match1 = False
    if re.search(r"(https|http):\/\/[^\/]+\/(live|movie|series)\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", ref_url) is not None:
        match1 = True

    match2 = False
    if re.search(r"(https|http):\/\/[^\/]+\/[^\/]+\/[^\/]+\/\d+(\.m3u8|\.ts|$)", ref_url) is not None:
        match2 = True

    if match1:
        username = re.search(r"[^\/]+(?=\/[^\/]+\/\d+\.)", ref_url).group()
        password = re.search(r"[^\/]+(?=\/\d+\.)", ref_url).group()
        domain = re.search(r"(https|http):\/\/[^\/]+", ref_url).group()

    elif match2:
        username = re.search(r"[^\/]+(?=\/[^\/]+\/[^\/]+$)", ref_url).group()
        password = re.search(r"[^\/]+(?=\/[^\/]+$)", ref_url).group()
        domain = re.search(r"(https|http):\/\/[^\/]+", ref_url).group()

    get_live_streams = "%s/player_api.php?username=%s&password=%s&action=get_live_streams" % (domain, username, password)
    retries = Retry(total=1, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    response = ""

    try:
        r = http.get(get_live_streams, headers=hdr, timeout=10, verify=False)
        r.raise_for_status()
        if r.status_code == requests.codes.ok:
            try:
                response = r.json()
            except Exception as ex:
                print(ex)

    except Exception as exc:
        print(exc)

    if response:
        live_streams = response

        is_catchup_channel = False
        for channel in live_streams:
            if channel["stream_id"] == ref_stream_num and int(channel["tv_archive"]) == 1:
                is_catchup_channel = True
                break

    if live_streams and is_catchup_channel:
        from . import catchup

        if (originalrefstring == selected_ref_string) or (urljoin(original_path, "/") == urljoin(ref_url, "/")):
            self.session.nav.stopService()
            self.session.openWithCallback(self.playOriginalChannel, catchup.BmxCatchup)
        else:
            self.session.open(catchup.BmxCatchup)


def playOriginalChannel(self, answer=None):
    self.session.nav.playService(eServiceReference(originalrefstring))


def Plugins(**kwargs):
    addFont(os.path.join(font_folder, "slyk-medium.ttf"), "slykregular", 100, 0)
    addFont(os.path.join(font_folder, "slyk-bold.ttf"), "slykbold", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-regular.ttf"), "bmxregular", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-medium.ttf"), "bmxbold", 100, 0)

    iconFile = "icons/plugin-icon_sd.png"
    if screenwidth.width() > 1280:
        iconFile = "icons/plugin-icon.png"
    description = _("IPTV Bouquets Creator by KiddaC")
    pluginname = _("BouquetMakerXtream")

    main_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_MENU, fnc=mainmenu, needsRestart=True)

    extensions_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=extensionsmenu, needsRestart=True)

    result = [
        PluginDescriptor(
            name=pluginname,
            description=description,
            where=[
                PluginDescriptor.WHERE_AUTOSTART,
                PluginDescriptor.WHERE_SESSIONSTART
            ],
            fnc=autostart,
        ),
        PluginDescriptor(
            name=pluginname,
            description=description,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=iconFile,
            fnc=main
        ),
    ]

    result.append(extensions_menu)

    if cfg.main.getValue():
        result.append(main_menu)

    return result
