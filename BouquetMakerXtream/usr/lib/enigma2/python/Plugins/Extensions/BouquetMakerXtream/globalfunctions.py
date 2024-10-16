#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, cfg

from enigma import eDVBDB
from requests.adapters import HTTPAdapter

import json
import os
import re
import requests

hdr = {'User-Agent': str(cfg.useragent.value)}


def getPlaylistJson():
    playlists_all = []
    if os.path.isfile(playlists_json) and os.stat(playlists_json).st_size > 0:
        with open(playlists_json) as f:
            try:
                playlists_all = json.load(f)
            except:
                os.remove(playlists_json)
    return playlists_all


def refreshBouquets():
    eDVBDB.getInstance().reloadServicelist()
    eDVBDB.getInstance().reloadBouquets()


def downloadUrl(url, ext):
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    r = ""
    try:
        r = http.get(url, headers=hdr, timeout=(20, 60), verify=False)
        r.raise_for_status()
        if r.status_code == requests.codes.ok:
            try:
                if ext == "json":
                    response = r.json()
                else:
                    response = r.content
                return response
            except Exception as e:
                print(e)
                return ""

    except Exception as e:
        print(e)

    return ""


def downloadApi(url):
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    r = ""
    try:
        r = http.get(url, headers=hdr, timeout=5, verify=False)
        r.raise_for_status()
        if r.status_code == requests.codes.ok:
            try:
                response = r.json()
                return response
            except Exception as e:
                print(e)
                return ""

    except Exception as e:
        print(e)

    return ""


def downloadUrlMulti(url):
    category = url[1]
    ext = url[2]
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    response = ""

    try:
        r = http.get(url[0], headers=hdr, timeout=(10, 30), verify=False, stream=True)
        r.raise_for_status()

        if r.status_code == requests.codes.ok:
            try:
                if ext == "json":
                    response = category, r.json()
                else:
                    content = bytearray()
                    for chunk in r.iter_content(chunk_size=32768):
                        content.extend(chunk)
                    response = category, content.decode("utf-8", errors='replace')
                return response
            except Exception as e:
                print("Error during processing response: {}".format(str(e)))
                return category, ""

    except requests.Timeout as e:
        print("*** Request timed out ***")
        print("Error message: {}".format(str(e)))
        return category, ""
    except requests.RequestException as e:
        print("*** Request failed ***")
        print("Error message: {}".format(str(e)))
        return category, ""


def safeName(name):
    name = name.encode("ascii", errors="ignore").decode()
    name = re.sub(r"[\<\>\:\"\/\\\|\?\*]", "_", str(name))
    name = re.sub(r" ", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name


def purge(my_dir, pattern):
    try:
        for f in os.listdir(my_dir):
            file_path = os.path.join(my_dir, f)
            if os.path.isfile(file_path):
                if re.search(pattern, f):
                    os.remove(file_path)
    except Exception as e:
        print(e)
