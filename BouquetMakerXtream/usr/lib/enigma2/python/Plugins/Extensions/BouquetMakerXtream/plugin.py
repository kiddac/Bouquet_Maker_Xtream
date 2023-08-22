#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigDirectory, ConfigYesNo, ConfigSelectionNumber, ConfigClock, ConfigPIN, ConfigInteger
from enigma import eTimer, getDesktop, addFont
from Plugins.Plugin import PluginDescriptor

import os
import shutil
import sys
import twisted.python.runtime

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
dir_tmp = "/tmp/bouquetmakerxtream/"
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

cfg.livetype = ConfigSelection(default="4097", choices=live_streamtype_choices)
cfg.vodtype = ConfigSelection(default="4097", choices=vod_streamtype_choices)

cfg.location = ConfigDirectory(default=dir_etc)
cfg.locallocation = ConfigDirectory(default=dir_etc)
cfg.main = ConfigYesNo(default=True)
cfg.skin = ConfigSelection(default="default", choices=folders)
cfg.parental = ConfigYesNo(default=False)
cfg.timeout = ConfigSelectionNumber(1, 20, 1, default=10, wraparound=True)
cfg.catchup = ConfigYesNo(default=False)
cfg.catchupprefix = ConfigSelection(default="~", choices=[("~", "~"), ("!", "!"), ("#", "#"), ("-", "-"), ("<", "<"), ("^", "^")])
cfg.catchupstart = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.catchupend = ConfigSelectionNumber(0, 30, 1, default=0, wraparound=True)
cfg.skipplaylistsscreen = ConfigYesNo(default=False)
cfg.wakeup = ConfigClock(default=((9 * 60) + 15) * 60)  # 10:15
cfg.adult = ConfigYesNo(default=False)
cfg.adultpin = ConfigPIN(default=0000)
cfg.retries = ConfigSubsection()
cfg.retries.adultpin = ConfigSubsection()
cfg.retries.adultpin.tries = ConfigInteger(default=3)
cfg.retries.adultpin.time = ConfigInteger(default=3)
cfg.autoupdate = ConfigYesNo(default=False)
cfg.groups = ConfigYesNo(default=False)
cfg.locationvalid = ConfigYesNo(default=True)
cfg.position = ConfigSelection(default="bottom", choices=[("bottom", _("Bottom")), ("top", _("Top"))])

skin_path = os.path.join(skin_directory, cfg.skin.value)
common_path = os.path.join(skin_directory, "common/")
playlists_json = os.path.join(dir_etc, "playlists.json")
playlist_file = os.path.join(dir_etc, "playlists.txt")

location = cfg.location.getValue()
if location:
    if os.path.exists(location):
        playlist_file = os.path.join(cfg.location.value, "playlists.txt")
        cfg.locationvalid.setValue(True)
        cfg.save()
    else:
        cfg.location.setValue(dir_etc)
        cfg.locationvalid.setValue(False)
        cfg.save()

font_folder = os.path.join(dir_plugins, "fonts/")

hdr = {"User-Agent": "Enigma2 - BouquetMakerXtream Plugin"}

# create folder for working files
if not os.path.exists(dir_etc):
    os.makedirs(dir_etc)

# delete temporary folder and contents
if os.path.exists(dir_tmp):
    shutil.rmtree("/tmp/bouquetmakerxtream")

# create temporary folder for downloaded files
if not os.path.exists(dir_tmp):
    os.makedirs(dir_tmp)

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
    session.open(mainmenu.BouquetMakerXtream_MainMenu)
    return


def mainmenu(menu_id, **kwargs):
    if menu_id == "mainmenu":
        return [(_("Bouquet Maker Xtream"), main, "BouquetMakerXtream", 49)]
    else:
        return []


def extensionsmenu(session, **kwargs):
    from . import mainmenu
    session.open(mainmenu.BouquetMakerXtream_MainMenu)
    return


autoStartTimer = None


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
        import time
        if cfg.autoupdate.value:
            clock = cfg.wakeup.value
            nowt = time.time()
            now = time.localtime(nowt)
            return int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, clock[0], clock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
        else:
            return -1

    def update(self, atLeast=0):
        import time
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
        return wake

    def onTimer(self):
        import time
        self.timer.stop()
        now = int(time.time())
        wake = self.getWakeTime()
        atLeast = 0
        if abs(wake - now) < 60:
            self.runUpdate()
            atLeast = 60
        self.update(atLeast)

    def runUpdate(self):
        print("\n *********** Updating BouquetMakerXtream Bouquets************ \n")
        from . import update
        self.session.open(update.BouquetMakerXtream_Update, "auto")
        # update.BouquetMakerXtream_Update()


def autostart(reason, session=None, **kwargs):
    global autoStartTimer
    if reason == 0:
        if session is not None:
            if autoStartTimer is None:
                autoStartTimer = AutoStartTimer(session)
    return


def Plugins(**kwargs):
    addFont(os.path.join(font_folder, "slyk-medium.ttf"), "slykregular", 100, 0)
    addFont(os.path.join(font_folder, "slyk-bold.ttf"), "slykbold", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-regular.ttf"), "bouquetregular", 100, 0)
    addFont(os.path.join(font_folder, "m-plus-rounded-1c-medium.ttf"), "bouquetbold", 100, 0)
    addFont(os.path.join(font_folder, "MavenPro-Regular.ttf"), "onyxregular", 100, 0)
    addFont(os.path.join(font_folder, "MavenPro-Medium.ttf"), "onyxbold", 100, 0)
    addFont(os.path.join(font_folder, "VSkin-Light.ttf"), "vskinregular", 100, 0)

    iconFile = "icons/plugin-icon_sd.png"
    if screenwidth.width() > 1280:
        iconFile = "icons/plugin-icon.png"
    description = (_("IPTV Bouquets Creator by KiddaC"))
    pluginname = (_("BouquetMakerXtream"))

    main_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_MENU, fnc=mainmenu, needsRestart=True)

    extensions_menu = PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=extensionsmenu, needsRestart=True)

    """
    result = [PluginDescriptor(name=pluginname, description=description, where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart),
              PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_PLUGINMENU, icon=iconFile, fnc=main)]
              """
    result = [PluginDescriptor(name=pluginname, description=description, where=PluginDescriptor.WHERE_PLUGINMENU, icon=iconFile, fnc=main)]

    result.append(extensions_menu)

    if cfg.main.getValue():
        result.append(main_menu)

    return result
