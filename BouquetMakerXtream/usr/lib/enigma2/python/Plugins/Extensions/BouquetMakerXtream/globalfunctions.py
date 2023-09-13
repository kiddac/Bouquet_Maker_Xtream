#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, hdr

from enigma import eDVBDB
from requests.adapters import HTTPAdapter

import json
import os
import re
import requests


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


def download_url(url, ext):
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    r = ""
    try:
        r = http.get(url, headers=hdr, timeout=(10, 30), verify=False)
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


def download_url_multi(url):

    category = url[1]
    ext = url[2]
    # print("**** url ***", url)
    r = ""
    retries = 1
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    response = ""
    try:
        r = http.get(url[0], headers=hdr, timeout=(10, 30), verify=False)
        r.raise_for_status()
        if r.status_code == requests.codes.ok:

            try:
                if ext == "json":
                    response = category, r.json()
                else:
                    response = category, r.text
                return response
            except Exception as e:
                print(e)
                return category, ""

    except Exception as e:
        print(e)

    return category, ""


def safeName(name):
    name = name.encode('ascii', errors='ignore').decode()
    name = re.sub(r'[\<\>\:\"\/\\\|\?\*]', "_", str(name))
    name = re.sub(r" ", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name


def purge(dir, pattern):
    for f in os.listdir(dir):
        file_path = os.path.join(dir, f)
        if os.path.isfile(file_path):
            if re.search(pattern, f):
                os.remove(file_path)
