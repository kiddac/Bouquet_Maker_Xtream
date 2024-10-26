#!/usr/bin/python
# -*- coding: utf-8 -*-

# Standard library imports
import os
import re
import requests
import shutil
import sys
import time
import twisted.python.runtime
from datetime import datetime
from requests.adapters import HTTPAdapter, Retry


try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin


# Enigma2 components
from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigDirectory, ConfigYesNo, ConfigSelectionNumber, ConfigClock, ConfigPIN, ConfigInteger, configfile
from enigma import addFont, eServiceReference, eTimer, getDesktop
from Plugins.Plugin import PluginDescriptor
from Screens.ChannelSelection import ChannelSelectionBase
from ServiceReference import ServiceReference

# Local application/library-specific imports
from . import _
from . import bouquet_globals as glob

try:
    from multiprocessing.pool import ThreadPool
    hasMultiprocessing = True
except ImportError:
    hasMultiprocessing = False

try:
    from concurrent.futures import ThreadPoolExecutor
    if twisted.python.runtime.platform.supportsThreads():
        hasConcurrent = True
    else:
        hasConcurrent = False
except ImportError:
    hasConcurrent = False

pythonFull = float(str(sys.version_info.major) + "." + str(sys.version_info.minor))
pythonVer = sys.version_info.major

epgimporter = False
if os.path.isdir("/usr/lib/enigma2/python/Plugins/Extensions/EPGImport"):
    epgimporter = True

isDreambox = os.path.exists("/usr/bin/apt-get")

with open("/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/version.txt", "r") as f:
    version = f.readline()

screenwidth = getDesktop(0).size()

dir_etc = "/etc/enigma2/bouquetmakerxtream/"
dir_plugins = "/usr/lib/enigma2/python/Plugins/Extensions/BouquetMakerXtream/"
dir_custom = "/media/hdd/picon/"

dir_tmp = "/tmp/bouquetmakerxtream/"

# delete temporary folder and contents
if os.path.exists(dir_tmp):
    shutil.rmtree(dir_tmp)

# create temporary folder for downloaded files
if not os.path.exists(dir_tmp):
    os.makedirs(dir_tmp)

if screenwidth.width() == 2560:
    skin_directory = os.path.join(dir_plugins, "skin/uhd/")
elif screenwidth.width() > 1280:
    skin_directory = os.path.join(dir_plugins, "skin/fhd/")
else:
    skin_directory = os.path.join(dir_plugins, "skin/hd/")

folders = [folder for folder in os.listdir(skin_directory) if folder != "common"]

useragents = [
    ("Enigma2 - BouquetMakerXtream Plugin"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Chrome 124"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0", "Firefox 125"),
    ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36", "Android")
]

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

SizeList = [
    ("xpicons", _("XPicons - 220x132 Pixel")),
    ("zzzpicons", _("ZZZPicons - 400x240 Pixel"))]

cfg.live_type = ConfigSelection(default="4097", choices=live_stream_type_choices)
cfg.vod_type = ConfigSelection(default="4097", choices=vod_stream_type_choices)

cfg.location = ConfigDirectory(default=dir_etc)
cfg.local_location = ConfigDirectory(default=dir_etc)
cfg.main = ConfigYesNo(default=True)
cfg.skin = ConfigSelection(default="default", choices=folders)
cfg.parental = ConfigYesNo(default=False)
# cfg.timeout = ConfigSelectionNumber(1, 20, 1, default=10, wraparound=True)
cfg.catchup_on = ConfigYesNo(default=False)
cfg.catchup = ConfigYesNo(default=False)
cfg.catchup_prefix = ConfigSelection(default="~", choices=[("~", "~"), ("!", "!"), ("#", "#"), ("-", "-"), ("^", "^")])
cfg.catchup_start = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.catchup_end = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.skip_playlists_screen = ConfigYesNo(default=False)
cfg.wakeup = ConfigClock(default=((9 * 60) + 0) * 60)  # 10:00
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

cfg.picon_bitdepth = ConfigSelection(default="24bit", choices=[("24", _("24 Bit")), ("8bit", _("8 Bit"))])
cfg.picon_type = ConfigSelection(default="SRP", choices=[("SRP", _("Service Reference Picons")), ("SNP", _("Service Name Picons"))])
cfg.picon_overwrite = ConfigYesNo(default=False)
cfg.picon_size = ConfigSelection(default="xpicons", choices=SizeList)
cfg.picon_custom = ConfigDirectory(default=dir_custom)
cfg.max_threads = ConfigSelectionNumber(5, 40, 5, default=20, wraparound=True)
cfg.picon_max_size = ConfigSelection(default="100000", choices=[("100000", _("100KB")), ("200000", _("200KB")), ("300000", _("300KB")), ("400000", _("400KB")), ("500000", _("500KB")), ("0", _("No limit"))])
cfg.picon_max_width = ConfigSelection(default="1000", choices=[("480", _("480px")), ("728", _("728px")), ("1000", _("1000px")), ("1280", _("1280px")), ("1920", _("1920px")), ("0", _("No limit"))])

cfg.picon_location = ConfigSelection(default="/media/hdd/picon/", choices=[
    ("/media/hdd/picon/", "/media/hdd/picon"),
    ("/media/usb/picon/", "/media/usb/picon"),
    ("/media/mmc/picon/", "/media/mmc/picon"),
    ("/usr/share/enigma2/picon/", "/usr/share/enigma2/picon"),
    ("/picons/piconHD/", "/picons/piconHD"),
    ("/data/picon/", "/data/picon"),
    ("/data/picons//piconHD/", "/data/picons/piconHD"),
    ("custom", "Custom location")
]
)

cfg.useragent = ConfigSelection(default="Enigma2 - BouquetMakerXtream Plugin", choices=useragents)

# vti picon symlink - ln -s /media/hdd/picon /usr/share/enigma2
# newenigma2 symlink - # ln -s /data/picons /picons

playlist_file = os.path.join(dir_etc, "playlists.txt")
playlists_json = os.path.join(dir_etc, "bmx_playlists.json")

# Set skin and font paths
skin_path = os.path.join(skin_directory, cfg.skin.value)
common_path = os.path.join(skin_directory, "common/")

location = cfg.location.value
if location:
    if os.path.exists(location):
        playlist_file = os.path.join(cfg.location.value, "playlists.txt")
        cfg.location_valid.setValue(True)
        cfg.save()
        configfile.save()
    else:
        os.makedirs(location)  # Create directory if it doesn't exist
        playlist_file = os.path.join(location, "playlists.txt")

        cfg.location_valid.setValue(True)
        cfg.save()
        configfile.save()
else:
    cfg.location.setValue(dir_etc)
    cfg.location_valid.setValue(False)
    cfg.save()
    configfile.save()

font_folder = os.path.join(dir_plugins, "fonts/")
addFont(os.path.join(font_folder, "slyk-medium.ttf"), "slykregular", 100, 0)
addFont(os.path.join(font_folder, "slyk-bold.ttf"), "slykbold", 100, 0)
addFont(os.path.join(font_folder, "m-plus-rounded-1c-regular.ttf"), "bmxregular", 100, 0)
addFont(os.path.join(font_folder, "m-plus-rounded-1c-medium.ttf"), "bmxbold", 100, 0)

hdr = {'User-Agent': 'Enigma2 - BouquetMakerXtream Plugin'}

# create folder for working files
if not os.path.exists(dir_etc):
    os.makedirs(dir_etc)

# check if playlists.txt file exists in specified location
if not os.path.isfile(playlist_file):
    with open(playlist_file, "a") as f:
        f.close()

# check if playlists.json file exists in specified location
if not os.path.isfile(playlists_json):
    with open(playlists_json, "a") as f:
        f.close()

# try and override epgimport settings
try:
    config.plugins.epgimport.import_onlybouquet.value = False
    config.plugins.epgimport.import_onlybouquet.save()
    configfile.save()
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


# Global variables
autoStartTimer = None
originalref = None
originalrefstring = None

original_ChannelSelectionBase = ChannelSelectionBase.__init__
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
            return int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, clock[0], clock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
        else:
            return -1

    def update(self, atLeast=0):
        self.timer.stop()
        wake = self.getWakeTime()
        nowtime = time.time()

        if wake > 0:
            if wake < nowtime + atLeast:
                # Tomorrow.
                wake += 24 * 3600
            next = wake - int(nowtime)
            if next > 3600:
                next = 3600
            if next <= 0:
                next = 60
            self.timer.startLongTimer(next)
        else:
            wake = -1

        wdt = datetime.fromtimestamp(wake)
        ndt = datetime.fromtimestamp(int(nowtime))

        print("[BouquetMakerXtream] WakeUpTime now set to", wdt, "(now=%s)" % ndt)
        return wake

    def onTimer(self):
        self.timer.stop()
        now = int(time.time())
        wake = self.getWakeTime()
        atLeast = 0
        if abs(wake - now) < 60:
            self.runUpdate()
            atLeast = 60
        self.update(atLeast)

    def runUpdate(self):
        print("\n *********** BouquetMakerXtream runupdate ************ \n")
        from . import update

        self.session.open(update.BmxUpdate, "auto")


def myBase(self, session, forceLegacy=False):
    original_ChannelSelectionBase(self, session)

    ChannelSelectionBase.showBmxCatchup = showBmxCatchup
    ChannelSelectionBase.playOriginalChannel = playOriginalChannel

    self["BmxCatchupAction"] = HelpableActionMap(self, "BMXCatchupActions", {
        "catchup": self.showBmxCatchup,
    })


def autostart(reason, session=None, **kwargs):
    # called with reason=1 to during shutdown, with reason=0 at startup?

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
                autoStartTimer = AutoStartTimer(_session)

            if cfg.catchup_on.value:
                if ChannelSelectionBase.__init__ != BmxChannelSelectionBase__init__:
                    ChannelSelectionBase.__init__ = myBase


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
    iconFile = "icons/plugin-icon_sd.png"
    if screenwidth.width() > 1280:
        iconFile = "icons/plugin-icon.png"
    description = _("IPTV Bouquets Creator by KiddaC")
    pluginname = _("BouquetMakerXtream")

    main_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_MENU, fnc=mainmenu, needsRestart=True)
    extensions_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main, needsRestart=True)

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

    if cfg.main.value:
        result.append(main_menu)

    return result
