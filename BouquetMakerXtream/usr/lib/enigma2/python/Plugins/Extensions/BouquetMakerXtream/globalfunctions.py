#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, cfg

from enigma import eDVBDB
from requests.adapters import HTTPAdapter

import json
import os
import re
import requests

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate'
}


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
    finally:
        http.close()
    return ""


def downloadApi(url):
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
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
    finally:
        http.close()
    return ""


def downloadUrlCategory(url):
    category = url[1]
    ext = url[2]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)

    try:
        r = http.get(url[0], headers=hdr, timeout=20, verify=False)
        r.raise_for_status()

        if r.status_code == requests.codes.ok:
            if ext == "json":
                response = category, r.json()
            else:
                response = category, r.text
            return response

    except Exception as e:
        print(e)
        return category, ""
    finally:
        http.close()


def downloadUrlMulti(url, output_file=None):
    category = url[1]
    ext = url[2]
    r = ""
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)

    try:
        print("\t[DEBUG] Starting download for URL: {}".format(url[0]))
        r = http.get(url[0], headers=hdr, timeout=(20, 300), verify=False, stream=True)
        r.raise_for_status()

        if r.status_code == requests.codes.ok:
            print("\t[DEBUG] Received response. Status code: {}".format(r.status_code))

            if ext == "json":
                json_content = r.json()
                return category, json_content
            else:
                output_dir = os.path.dirname(output_file)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                print("\t[DEBUG] Writing file to: {}".format(output_file))

                # Use a larger chunk size (e.g., 128 KB) for faster writing
                chunk_size = 8192 * 8  # 128 KB
                with open(output_file, 'wb') as f:
                    for i, chunk in enumerate(r.iter_content(chunk_size=chunk_size)):
                        f.write(chunk)

                print("\t[DEBUG] File writing complete.")
                return category, output_file

    except requests.Timeout as e:
        print("Error message: {}".format(str(e)))
        return category, ""
    except requests.RequestException as e:
        print("Error message: {}".format(str(e)))
        return category, ""
    finally:
        http.close()


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
