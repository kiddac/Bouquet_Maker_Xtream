#!/usr/bin/python
# -*- coding: utf-8 -*-

import gettext
import os

from Components.Language import language
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

PLUGINLANGUAGEDOMAIN = "BouquetMakerXtream"
PLUGINLANGUAGEPATH = "Extensions/BouquetMakerXtream/locale"

ISDREAMOS = False
if os.path.exists("/var/lib/dpkg/status"):
    ISDREAMOS = True


def locale_init():
    if ISDREAMOS:  # check if opendreambox image
        lang = language.getLanguage()[:2]  # getLanguage returns e.g. "fi_FI" for "language_country"
        os.environ["LANGUAGE"] = lang  # Enigma doesn't set this (or LC_ALL, LC_MESSAGES, LANG). gettext needs it!
    gettext.bindtextdomain(PLUGINLANGUAGEDOMAIN, resolveFilename(SCOPE_PLUGINS, PLUGINLANGUAGEPATH))


if ISDREAMOS:  # check if DreamOS image
    _ = lambda txt: gettext.dgettext(PLUGINLANGUAGEDOMAIN, txt) if txt else ""
else:
    def _(txt):
        if gettext.dgettext(PLUGINLANGUAGEDOMAIN, txt):
            return gettext.dgettext(PLUGINLANGUAGEDOMAIN, txt)

        print("[%s] fallback to default translation for %s" % (PLUGINLANGUAGEDOMAIN, txt))
        return gettext.gettext(txt)
locale_init()
language.addCallback(locale_init)
