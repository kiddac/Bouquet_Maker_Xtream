#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import _
from .plugin import skin_directory, cfg, hasConcurrent, hasMultiprocessing, pythonVer
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from PIL import Image, ImageFile, PngImagePlugin, ImageChops
from requests.adapters import HTTPAdapter, Retry
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from struct import unpack_from

import io
import os
import re
import requests


ImageFile.LOAD_TRUNCATED_IMAGES = True

_simple_palette = re.compile(b"^\xff*\x00\xff*$")


def i16(c, o=0):
    return unpack_from(">H", c, o)[0]


def mycall(self, cid, pos, length):
    if cid.decode("ascii") == "tRNS":
        return self.chunk_TRNS(pos, length)
    else:
        return getattr(self, "chunk_" + cid.decode("ascii"))(pos, length)


def mychunk_TRNS(self, pos, length):
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


if pythonVer != 2:
    PngImagePlugin.ChunkStream.call = mycall
    PngImagePlugin.PngStream.chunk_TRNS = mychunk_TRNS


try:
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 0
except:
    from httplib import HTTPConnection
    HTTPConnection.debuglevel = 0


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

        self["action"] = Label(_("Building Picons..."))
        self["status"] = Label("")
        self["progress"] = ProgressBar()

        self["actions"] = ActionMap(["BMXActions"], {
            "cancel": self.keyCancel
        }, -2)

        self.job_current = 0
        self.job_picon_name = ""
        self.job_total = len(self.selected)
        self.picon_num = 0
        self.pause = 100
        self.complete = False
        self.onFirstExecBegin.append(self.start)

        os.system("echo 1 > /proc/sys/vm/drop_caches")
        os.system("echo 2 > /proc/sys/vm/drop_caches")
        os.system("echo 3 > /proc/sys/vm/drop_caches")

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

            self.timer = eTimer()
            try:
                self.timer_conn = self.timer.timeout.connect(self.buildPicons)
            except:
                try:
                    self.timer.callback.append(self.buildPicons)
                except:
                    self.buildPicons()
            self.timer.start(100, True)

        else:
            self.showError(_("No picons selected."))

    def fetch_url(self, url, i):
        maxsize = False

        url[i][1] = url[i][1].replace("728px", "220px")
        url[i][1] = url[i][1].replace("1200px", "220px")
        url[i][1] = url[i][1].replace("1280px", "220px")
        url[i][1] = url[i][1].replace("1920px", "220px")
        url[i][1] = url[i][1].replace("2000px", "220px")

        image_formats = ("image/png", "image/jpeg", "image/jpg")
        retries = Retry(total=1, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        http = requests.Session()
        http.mount("http://", adapter)
        http.mount("https://", adapter)
        # http.verify = True

        response = ""
        try:
            response = http.get(url[i][1], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", "Accept": "image/png,image/jpeg"}, stream=True, timeout=5, verify=False, allow_redirects=False)
            if response:

                if response.status_code == 200:
                    if "content-length" in response.headers and int(response.headers["content-length"]) > 100000:
                        print("*** Picon source too large ***", url[i])
                        maxsize = True

                    if "content-type" in response.headers and maxsize is False:
                        if response.headers["content-type"] in image_formats:
                            try:
                                content = response.content

                                if pythonVer == 3:
                                    if content.startswith(b"\x89PNG") or content.startswith(b"\xff\xd8\xff"):
                                        image_file = io.BytesIO(content)
                                        self.makePicon(image_file,  url[i][0], url[i][1])
                                elif content.startswith("\x89PNG") or content.startswith("\xff\xd8\xff"):
                                    image_file = io.BytesIO(content)
                                    self.makePicon(image_file,  url[i][0], url[i][1])

                            except Exception as e:
                                print(e)
                                print("**** bad response***", url[i][1])

            else:
                print("*** no response ***")

        except Exception as e:
            print(e)

    def log_result(self, result=None):
        self.progresscurrent += 1
        self["action"].setText(_("Making BouquetMakerXtream Picons"))
        self["progress"].setValue(self.progresscurrent)
        self["status"].setText("Picon %d of %d" % (self.progresscurrent, self.job_total))
        if self.progresscurrent == self.job_total - 1 or self.progresscurrent == self.job_total:

            self.timer3 = eTimer()
            try:
                self.timer3_conn = self.timer3.timeout.connect(self.finished)
            except:
                try:
                    self.timer3.callback.append(self.finished)
                except:
                    self.self.finished()
            self.timer3.start(3000, True)

    def buildPicons(self):
        results = ""

        threads = len(self.selected)
        if threads > 30:
            threads = 30

        if hasConcurrent:
            try:
                from concurrent.futures import ThreadPoolExecutor
                executor = ThreadPoolExecutor(max_workers=threads)

                for i in range(self.job_total):
                    # self.progresscurrent += 1

                    try:
                        results = executor.submit(self.fetch_url, self.selected, i)
                        try:
                            results.add_done_callback(self.log_result)
                        except Exception as e:
                            print(e)
                    except Exception as e:
                        print(e)

            except Exception as e:
                print(e)

        elif hasMultiprocessing:
            try:
                from multiprocessing.pool import ThreadPool
                pool = ThreadPool(threads)

                for i in range(self.job_total):
                    try:
                        pool.apply_async(self.fetch_url, args=(self.selected, i), callback=self.log_result)
                    except Exception as e:
                        print(e)

                pool.close()

            except Exception as e:
                print(e)

    def finished(self):
        if self.complete is False:
            self.complete = True
            self.done()

    def showError(self, message):
        question = self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)
        question.setTitle(_("Create Picons"))
        self.close()

    def done(self, answer=None):
        self.close()

    def makePicon(self, image_file, piconname, url):
        piconSize = [220, 132]
        self.bitdepth = "24bit"  # "8bit"
        self.downloadlocation = cfg.picon_location.value
        im = None
        imagetype = ""

        if image_file:
            try:
                im = Image.open(image_file)
            except IOError:
                return
            except Exception:
                return

            # get image format
            imagetype = im.format

            if (im.size[1] > 1000 or im.size[0] > 1000):
                return

            # create blank image
            width, height = piconSize
            blank = Image.new("RGBA", (width, height), (255, 255, 255, 0))

            im = im.convert("RGBA")

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

                except Exception as e:
                    print("*** lanczos failed ***", e)
                    try:
                        im.thumbnail(thumbsize, Image.ANTIALIAS)

                    except Exception as e:
                        print("*** antialias failed ***", e)

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

                # save picon
                im.save(self.downloadlocation + "/" + piconname + ".png", optimize=True)
                im.close()

            except Exception as e:
                print(e, piconname, url)
                return
            except IOError as oe:
                print(oe, piconname, url)
                return
            except:
                print(piconname, url)
                return

        else:
            width, height = piconSize
            blank = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            blank.save(self.downloadlocation + "/" + piconname + ".png", optimize=True)
            blank.close()

    def savePicon(self, im, piconname):
        if not os.path.exists(self.downloadlocation):
            os.makedirs(self.downloadlocation)

        try:
            if self.bitdepth == "8bit":
                alpha = im.split()[-1]
                im = im.convert("RGB").convert("P", palette=Image.ADAPTIVE)
                mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                im.paste(255, mask)
                im.save(self.downloadlocation + "/" + piconname + ".png", transparency=255)
                # im.close()
            else:
                im.save(self.downloadlocation + "/" + piconname + ".png", optimize=True)
                # im.close()

            os.system("echo 1 > /proc/sys/vm/drop_caches")
            os.system("echo 2 > /proc/sys/vm/drop_caches")
            os.system("echo 3 > /proc/sys/vm/drop_caches")
        except Exception as e:
            print("*** failed to save ***", e)
