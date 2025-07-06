#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from .plugin import skin_directory, cfg, hasConcurrent, hasMultiprocessing, pythonVer, dir_custom
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from PIL import Image, ImageFile, PngImagePlugin, ImageChops
from requests.adapters import HTTPAdapter, Retry
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

import io
import os
import re
import requests
import string

ImageFile.LOAD_TRUNCATED_IMAGES = True

_simple_palette = re.compile(b"^\xff*\x00\xff*$")


# png code courtest of adw on stackoverflow
def patched_chunk_tRNS(self, pos, len):
    i16 = PngImagePlugin.i16
    s = ImageFile._safe_read(self.fp, len)
    if self.im_mode == "P":
        i = string.find(s, chr(0))
        if i >= 0:
            self.im_info["transparency"] = map(ord, s)
    elif self.im_mode == "L":
        self.im_info["transparency"] = i16(s)
    elif self.im_mode == "RGB":
        self.im_info["transparency"] = (i16(s), i16(s[2:]), i16(s[4:]))
    return s


# png code courtest of adw on stackoverflow
def patched_load(self):
    if self.im and self.palette and self.palette.dirty:
        self.im.putpalette(*self.palette.getdata())
        self.palette.dirty = 0
        self.palette.rawmode = None
        try:
            trans = self.info["transparency"]
        except KeyError:
            self.palette.mode = "RGB"
        else:
            try:
                for i, a in enumerate(trans):
                    self.im.putpalettealpha(i, a)
            except TypeError:
                self.im.putpalettealpha(trans, 0)
            self.palette.mode = "RGBA"
    if self.im:
        return self.im.pixel_access(self.readonly)


def mycall(self, cid, pos, length):
    if cid.decode("ascii") == "tRNS":
        return self.chunk_TRNS(pos, length)
    else:
        return getattr(self, "chunk_" + cid.decode("ascii"))(pos, length)


def mychunk_TRNS(self, pos, length):
    i16 = PngImagePlugin.i16
    s = ImageFile._safe_read(self.fp, length)
    if self.im_mode == "P":
        if _simple_palette.match(s):
            i = s.find(b"\0")
            if i >= 0:
                self.im_info["transparency"] = i
        else:
            self.im_info["transparency"] = s
    elif self.im_mode in ("1", "L", "I"):
        self.im_info["transparency"] = i16(s)
    elif self.im_mode == "RGB":
        self.im_info["transparency"] = i16(s), i16(s, 2), i16(s, 4)
    return s


if pythonVer == 2:
    Image.Image.load = patched_load
    PngImagePlugin.PngStream.chunk_tRNS = patched_chunk_tRNS
else:
    PngImagePlugin.ChunkStream.call = mycall
    PngImagePlugin.PngStream.chunk_TRNS = mychunk_TRNS


try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Accept-Encoding': 'gzip, deflate'
}


class BmxDownloadPicons(Screen):

    def __init__(self, session, selected):
        self.selected = selected

        Screen.__init__(self, session)
        self.session = session

        skin_path = os.path.join(skin_directory, cfg.skin.getValue())
        skin = os.path.join(skin_path, "progress.xml")
        with open(skin, "r") as f:
            self.skin = f.read()

        self.setup_title = _("Downloadng Picons")

        self["action"] = Label(_("Making BouquetMakerXtream Picons"))
        self["info"] = Label("")
        self["status"] = Label("")
        self["progress"] = ProgressBar()

        self["actions"] = ActionMap(["BMXActions"], {
            "cancel": self.keyCancel
        }, -2)

        if cfg.picon_location.value == "custom" and str(cfg.picon_location.value) != str(dir_custom):
            self.downloadlocation = cfg.picon_custom.value
        else:
            self.downloadlocation = cfg.picon_location.value

        if not os.path.exists(self.downloadlocation):
            try:
                os.makedirs(self.downloadlocation)
            except Exception as e:
                print(e)
                return

        self.job_current = 0
        self.job_picon_name = ""
        self.job_total = len(self.selected)
        self.picon_num = 0
        self.complete = False

        self.badurlcount = 0
        self.typecount = 0
        self.existscount = 0
        self.sizecount = 0
        self.successcount = 0

        self.badurllist = []
        self.typelist = []
        self.existslist = []
        self.sizelist = []
        self.successlist = []

        self.bitdepth = cfg.picon_bitdepth.value
        self.piconsize = cfg.picon_size.value
        self.overwrite = cfg.picon_overwrite.value

        self.blockinglist = []
        self.sizeblockinglist = []
        self.typeblockinglist = []

        os.system("echo 1 > /proc/sys/vm/drop_caches")
        os.system("echo 2 > /proc/sys/vm/drop_caches")
        os.system("echo 3 > /proc/sys/vm/drop_caches")
        
        self.timer = eTimer()
        self.timer3 = eTimer()

        """
        self.finishedtimer = eTimer()

        try:
            self.finishedtimer_conn = self.finishedtimer.timeout.connect(self.check_finished)
        except:
            self.finishedtimer.callback.append(self.check_finished)

        self.finishedtimer.start(2000, False)

        self.onFirstExecBegin.append(self.start)
        """

        self.updatedisplaytimer = eTimer()

        try:
            self.updatedisplaytimer_conn = self.updatedisplaytimer.timeout.connect(self.log_result)
        except:
            self.updatedisplaytimer.callback.append(self.log_result)

        self.updatedisplaytimer.start(1000, False)

        self.onFirstExecBegin.append(self.start)

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def keyCancel(self):
        self.close()

    def start(self):
        if self.job_total > 0:
            self.progresscount = self.job_total
            self.progresscurrent = 0
            self["progress"].setRange((0, self.progresscount))
            self["progress"].setValue(self.progresscurrent)

            try:
                self.timer_conn = self.timer.timeout.connect(self.buildPicons)
            except:
                try:
                    self.timer.callback.append(self.buildPicons)
                except:
                    self.buildPicons()
            self.timer.start(200, True)

        else:
            self.showError(_("No picons found."))

    def fetch_url(self, url, i):
        self.progresscurrent += 1
        if not cfg.picon_overwrite.value:
            if os.path.exists(str(self.downloadlocation) + str(url[i][0]) + ".png"):
                self.existscount += 1
                self.existslist.append(url[i])
                return

        if url[i][1] in self.blockinglist:
            self.barurlcount += 1
            self.badurllist.append(url[i])
            return

        if url[i][1] in self.sizeblockinglist:
            self.sizecount += 1
            self.sizelist.append(url[i])
            return

        if url[i][1] in self.typeblockinglist:
            self.typecount += 1
            self.typelist.append(url[i])
            return

        url[i][1] = url[i][1].replace("728px", "400px")
        url[i][1] = url[i][1].replace("1200px", "400px")
        url[i][1] = url[i][1].replace("1280px", "400px")
        url[i][1] = url[i][1].replace("1920px", "400px")
        url[i][1] = url[i][1].replace("2000px", "400px")

        image_formats = ("image/png", "image/jpeg")
        retries = Retry(total=0, backoff_factor=0)
        adapter = HTTPAdapter(max_retries=retries)

        with requests.Session() as http:
            http.mount("http://", adapter)
            http.mount("https://", adapter)

            try:
                response = http.get(url[i][1], headers=hdr, stream=True, timeout=5, verify=False, allow_redirects=False)
                if response:
                    if "content-length" in response.headers and int(cfg.picon_max_size.value) != 0:
                        if int(response.headers["content-length"]) > int(cfg.picon_max_size.value):
                            print("*** Picon source too large ***", url[i])
                            self.sizecount += 1
                            self.sizelist.append(url[i])
                            if url[i][1] not in self.sizeblockinglist:
                                self.sizeblockinglist.append(url[i][1])
                            return

                    if "content-type" in response.headers and response.headers["content-type"] in image_formats:
                        try:
                            content = response.content
                            image_file = io.BytesIO(content)
                            self.makePicon(image_file, url[i][0], url[i][1])
                            self.successcount += 1
                            self.successlist.append(url[i])
                            return

                        except Exception as e:
                            print("**** image builder failed***", e, url[i][1])
                            self.typecount += 1
                            self.typelist.append(url[i])
                            if url[i][1] not in self.typeblockinglist:
                                self.typeblockinglist.append(url[i][1])
                            return

                    else:
                        print("*** not png or jpeg ***", url[i][1])
                        self.typecount += 1
                        self.typelist.append(url[i])
                        if url[i][1] not in self.typeblockinglist:
                            self.typeblockinglist.append(url[i][1])
                        return
                else:
                    print("**** bad response***", url[i][1])
                    self.badurlcount += 1
                    self.badurllist.append(url[i])
                    if url[i][1] not in self.blockinglist:
                        self.blockinglist.append(url[i][1])
                        return

            except Exception as e:
                print("**** exception ***", url[i][1], e)
                self.badurlcount += 1
                self.badurllist.append(url[i])
                if url[i][1] not in self.blockinglist:
                    self.blockinglist.append(url[i][1])
                    return

    def log_result(self, result=None):
        # self.progresscurrent += 1
        self["progress"].setValue(self.progresscurrent)
        self["info"].setText(_("Success: " + "%s   " + _("Size: ") + "%s   " + _("Type: ") + "%s   " + _("Url: ") + "%s   " + _("Exists: ") + "%s") % (self.successcount, self.sizecount, self.typecount, self.badurlcount, self.existscount))
        self["status"].setText(_("Picon %d of %d") % (self.progresscurrent, self.job_total))

        if self.progresscurrent == self.job_total:
            self.updatedisplaytimer.stop()
            try:
                self.timer3_conn = self.timer3.timeout.connect(self.finished)
            except:
                try:
                    self.timer3.callback.append(self.finished)
                except:
                    self.finished()
            self.timer3.start(2000, True)

    def buildPicons(self):
        # results = ""

        threads = len(self.selected)
        if threads > int(cfg.max_threads.value):
            threads = int(cfg.max_threads.value)

        if hasConcurrent:
            # print("******* trying concurrent futures ******")
            try:
                from concurrent.futures import ThreadPoolExecutor
                executor = ThreadPoolExecutor(max_workers=threads)

                for i in range(self.job_total):
                    try:
                        executor.submit(self.fetch_url, self.selected, i)
                        # results = executor.submit(self.fetch_url, self.selected, i)
                        # results.add_done_callback(self.log_result)
                    except:
                        pass

            except Exception as e:
                print(e)

        elif hasMultiprocessing:
            # print("******* trying multiprocessing ******")
            try:
                from multiprocessing.pool import ThreadPool
                pool = ThreadPool(threads)

                for i in range(self.job_total):
                    try:
                        # pool.apply_async(self.fetch_url, args=(self.selected, i), callback=self.log_result)
                        pool.apply_async(self.fetch_url, args=(self.selected, i))
                    except:
                        pass

                pool.close()

            except Exception as e:
                print(e)

    def finished(self):
        # print("*** finished ***")
        if self.complete is False:

            with open('/tmp/bmxsuccesslist.txt', 'w+') as f:
                for item in self.successlist:
                    f.write("%s\n" % item)
                f.truncate()

            with open('/tmp/bmxbadlist.txt', 'w+') as f:
                for item in self.badurllist:
                    f.write("%s\n" % item)
                f.truncate()

            with open('/tmp/bmxtypelist.txt', 'w+') as f:
                for item in self.typelist:
                    f.write("%s\n" % item)
                f.truncate()

            with open('/tmp/bmxsizelist.txt', 'w+') as f:
                for item in self.sizelist:
                    f.write("%s\n" % item)
                f.truncate()

            with open('/tmp/bmxexistslist.txt', 'w+') as f:
                for item in self.existslist:
                    f.write("%s\n" % item)
                f.truncate()

            self.complete = True

            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")

            self.session.openWithCallback(
                self.close, MessageBox,
                _("Finished.\n\n") +
                _("Success: ") + str(self.successcount) + "   " + _("Bad size: ") + str(self.sizecount) + "   " + _("bad type: ") + str(self.typecount) + "   " + _("bad url: ") + str(self.badurlcount) + "   " + _("Exists: ") + str(self.existscount) + "\n\n" +
                _("Restart your GUI to refresh picons.") + "\n\n" + _("Your created picons can be found in") + "\n" + str(self.downloadlocation) + "\n\n" +
                _("Your failed picon list can be found in") + "\n" + "/tmp/", MessageBox.TYPE_INFO
            )

    def showError(self, message=None):
        question = self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)
        question.setTitle(_("Picon Error"))
        self.close()

    def makePicon(self, image_file, piconname, url):
        if self.piconsize == "xpicons":
            piconSize = [220, 132]
        elif self.piconsize == "zzzpicons":
            piconSize = [400, 240]

        im = None
        imagetype = ""

        if image_file:
            try:
                im = Image.open(image_file)
            except IOError:
                return
            except:
                return

            # get image format
            imagetype = im.format

            if int(cfg.picon_max_width.value) != 0 and im.size[0] > int(cfg.picon_max_width.value):
                return

            # create blank image
            width, height = piconSize
            blank = Image.new("RGBA", (width, height), (255, 255, 255, 0))

            try:
                im = im.convert("RGBA")
            except Exception as e:
                print(e)

            if imagetype == "PNG":
                # autocrop
                r, g, b, a = im.split()
                bbox = a.getbbox()
                im = im.crop(bbox)
                (width, height) = im.size
                cropped_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                cropped_image.paste(im, (0, 0))
                im = cropped_image

            try:
                # resize image
                width, height = piconSize
                thumbsize = [int(width), int(height)]

                try:
                    im.thumbnail(thumbsize, Image.Resampling.LANCZOS)
                except Exception:
                    try:
                        im.thumbnail(thumbsize, Image.ANTIALIAS)
                    except Exception:
                        pass

                # merge blank and resized image

                imagew, imageh = im.size
                im_alpha = im.convert("RGBA").split()[-1]

                bgwidth, bgheight = blank.size
                blank_alpha = blank.convert("RGBA").split()[-1]

                temp = Image.new("L", (bgwidth, bgheight), 0)
                temp.paste(im_alpha, ((bgwidth - imagew) // 2, (bgheight - imageh) // 2), im_alpha)

                blank_alpha = ImageChops.screen(blank_alpha, temp)
                blank.paste(im, ((bgwidth - imagew) // 2, (bgheight - imageh) // 2), im)
                blank.putalpha(blank_alpha)

                im = blank

                self.savePicon(im, piconname)

            except IOError as oe:
                print(oe, piconname, url)
                return

            except Exception as e:
                print(e, piconname, url)
                return

            except:
                print(piconname, url)
                return

        else:
            width, height = piconSize
            blank = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            self.savePicon(blank, piconname)

    def savePicon(self, im, piconname):
        try:
            if self.bitdepth == "8bit":
                alpha = im.split()[-1]
                im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE)
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                im.paste(255, mask)
                im.save(self.downloadlocation + "/" + piconname + ".png", transparency=255)
            else:
                im.save(self.downloadlocation + "/" + piconname + ".png", optimize=True)

        except Exception as e:
            print("*** failed to save ***", e)
