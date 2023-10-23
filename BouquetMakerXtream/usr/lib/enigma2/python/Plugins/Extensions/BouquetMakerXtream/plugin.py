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
except ImportError:
    from urllib.parse import urljoin

try:
    from multiprocessing.pool import ThreadPool

    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False

try:
    from concurrent.futures import ThreadPoolExecutor

    HAS_CONCURRENT = bool(twisted.python.runtime.platform.supportsThreads())
except Exception:
    HAS_CONCURRENT = False

PYTHON_FULL = float(str(sys.version_info.major) + "." + str(sys.version_info.minor))
PYTHON_VER = sys.version_info.major

EPGIMPORTER = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    EPGIMPORTER = True

ISDREAMBOX = False
if os.path.exists("/usr/bin/apt-get"):
    ISDREAMBOX = True

with open("/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/version.txt", "r") as f:
    VERSION = f.readline()

SCREENWIDTH = getDesktop(0).size()

DIR_ETC = "/etc/enigma2/bouquetmakerxtream/"
DIR_PLUGINS = "/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/"

if SCREENWIDTH.width() == 2560:
    SKIN_DIRECTORY = os.path.join(DIR_PLUGINS, "skin/uhd/")
elif SCREENWIDTH.width() > 1280:
    SKIN_DIRECTORY = os.path.join(DIR_PLUGINS, "skin/fhd/")
else:
    SKIN_DIRECTORY = os.path.join(DIR_PLUGINS, "skin/hd/")

folders = os.listdir(SKIN_DIRECTORY)
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

cfg.location = ConfigDirectory(default=DIR_ETC)
cfg.local_location = ConfigDirectory(default=DIR_ETC)
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

skin_path = os.path.join(SKIN_DIRECTORY, cfg.skin.value)
COMMON_PATH = os.path.join(SKIN_DIRECTORY, "common/")
PLAYLISTS_JSON = os.path.join(DIR_ETC, "bmx_playlists.json")
PLAYLIST_FILE = os.path.join(DIR_ETC, "playlists.txt")

location = cfg.location.getValue()
if location:
    if os.path.exists(location):
        PLAYLIST_FILE = os.path.join(cfg.location.value, "playlists.txt")
        cfg.location_valid.setValue(True)
        cfg.save()
    else:
        cfg.location.setValue(DIR_ETC)
        cfg.location_valid.setValue(False)
        cfg.save()

font_folder = os.path.join(DIR_PLUGINS, "fonts/")

HDR = {"User-Agent": "Enigma2 - BouquetMakerXtream Plugin"}

# create folder for working files
if not os.path.exists(DIR_ETC):
    os.makedirs(DIR_ETC)

# check if playlists.txt file exists in specified location
if not os.path.isfile(PLAYLIST_FILE):
    with open(PLAYLIST_FILE, "a") as f:
        f.close()

# check if playlists.json file exists in specified location
if not os.path.isfile(PLAYLISTS_JSON):
    with open(PLAYLISTS_JSON, "a") as f:
        f.close()

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
ORIGINAL_REF = None
ORIGINAL_REF_STRING = None
BmxChannelSelectionBase__init = None
_session = None


class AutoStartTimer:
    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.on_timer)
        except Exception:
            self.timer.callback.append(self.on_timer)
        self.update()

    def get_wake_time(self):
        if cfg.autoupdate.value:
            clock = cfg.wakeup.value
            nowt = time.time()
            now = time.localtime(nowt)
            waketime = int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, clock[0], clock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
            return waketime
        else:
            return -1

    def update(self, at_least=0):
        self.timer.stop()
        wake = self.get_wake_time()
        now_t = time.time()
        now = int(now_t)

        if wake > 0:
            if wake < now + at_least:
                wake += 24 * 3600  # add 24 hours to next wake time
            next = wake - now
            self.timer.startLongTimer(next)
        else:
            wake = -1

        wdt = datetime.fromtimestamp(wake)
        ndt = datetime.fromtimestamp(now)

        print("[BouquetMakerXtream] WakeUpTime now set to", wdt, "(now=%s)" % ndt)
        return wake

    def on_timer(self):
        self.timer.stop()
        now = int(time.time())
        wake = self.get_wake_time()
        # print("*** wake ", wake)
        at_least = 0
        if wake - now < 60:
            self.run_update()
            at_least = 60
        self.update(at_least)

    def run_update(self):
        print("\n *********** BouquetMakerXtream runupdate ************ \n")
        from . import update

        self.session.open(update.BmxUpdate, "auto")


def autostart(reason, session=None, **kwargs):
    # called with reason=1 to during shutdown, with reason=0 at startup?

    if cfg.catchup_on.getValue() is True and session is not None:
        global BmxChannelSelectionBase__init
        BmxChannelSelectionBase__init = ChannelSelectionBase.__init__
        ChannelSelectionBase.__init__ = MyChannelSelectionBase__init__
        ChannelSelectionBase.showBmxCatchup = show_bmx_catchup
        ChannelSelectionBase.play_original_channel = play_original_channel

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
    BmxChannelSelectionBase__init(self, session)
    self["BmxCatchupAction"] = HelpableActionMap(self, "BMXCatchupActions", {
        "catchup": self.showBmxCatchup,
    })


def show_bmx_catchup(self):
    try:
        global ORIGINAL_REF
        global ORIGINAL_REF_STRING
        ORIGINAL_REF = self.session.nav.getCurrentlyPlayingServiceReference()
        ORIGINAL_REF_STRING = ORIGINAL_REF.toString()
    except:
        pass

    selected_ref = self["list"].getCurrent()
    selected_ref_string = selected_ref.toString()

    glob.CURRENT_REF = ServiceReference(selected_ref)

    path = str(selected_ref.getPath())

    if "http" not in path:
        return

    glob.NAME = glob.CURRENT_REF.getServiceName()

    is_catchup_channel = False
    ref_url = ""
    ref_stream = ""
    ref_stream_num = ""
    username = ""
    password = ""
    domain = ""

    original_path = ServiceReference(ORIGINAL_REF).getPath()
    ref_url = glob.CURRENT_REF.getPath()

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
        r = http.get(get_live_streams, headers=HDR, timeout=10, verify=False)
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

        if (ORIGINAL_REF_STRING == selected_ref_string) or (urljoin(original_path, "/") == urljoin(ref_url, "/")):
            self.session.nav.stopService()
            self.session.openWithCallback(self.play_original_channel, catchup.BmxCatchup)
        else:
            self.session.open(catchup.BmxCatchup)


def play_original_channel(self, answer=None):
    self.session.nav.playService(eServiceReference(ORIGINAL_REF_STRING))


def Plugins(**kwargs):
    addFont(os.path.join(font_folder, "slyk-medium.ttf"), "slykregular", 100, 0)
    addFont(os.path.join(font_folder, "slyk-bold.ttf"), "slykbold", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-regular.ttf"), "bmxregular", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-medium.ttf"), "bmxbold", 100, 0)

    icon_file = "icons/plugin-icon_sd.png"
    if SCREENWIDTH.width() > 1280:
        icon_file = "icons/plugin-icon.png"
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
            icon=icon_file,
            fnc=main
        ),
    ]

    result.append(extensions_menu)

    if cfg.main.getValue():
        result.append(main_menu)

    return result
