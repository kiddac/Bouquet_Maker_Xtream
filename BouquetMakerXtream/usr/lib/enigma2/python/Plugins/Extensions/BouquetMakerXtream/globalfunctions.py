#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, cfg, pythonVer, debugs

from enigma import eDVBDB
from requests.adapters import HTTPAdapter

import json
import os
import re
import requests

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Accept-Encoding': 'gzip, deflate'
}


def getPlaylistJson():
    if debugs:
        print("*** getPlaylistJson ***")
    playlists_all = []
    if os.path.isfile(playlists_json) and os.stat(playlists_json).st_size > 0:
        with open(playlists_json) as f:
            try:
                playlists_all = json.load(f)
            except:
                os.remove(playlists_json)
    return playlists_all


def refreshBouquets():
    if debugs:
        print("*** refreshBouquets ***")
    eDVBDB.getInstance().reloadServicelist()
    eDVBDB.getInstance().reloadBouquets()


def downloadUrl(url, ext):
    if debugs:
        print("*** downloadUrl ***", url, ext)
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
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
                    print("Error processing response:", e)
                    return ""
        except Exception as e:
            print("Request failed:", e)

    return ""


def downloadApi(url):
    if debugs:
        print("*** downloadApi ***", url)
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
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
                    print("Error processing JSON response:", e)
                    return ""
        except Exception as e:
            print("Request failed:", e)

    return ""


def downloadUrlCategory(url):
    if debugs:
        print("*** downloadUrlCategory ***", url)
    category = url[1]
    ext = url[2]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url[0], headers=hdr, timeout=20, verify=False)
            r.raise_for_status()

            if r.status_code == requests.codes.ok:
                if ext == "json":
                    response = (category, r.json())
                else:
                    response = (category, r.text)
                return response

        except Exception as e:
            print("Request failed:", e)
            return category, ""

    return category, ""


def downloadUrlMulti(url, output_file=None):
    if debugs:
        print("*** downloadUrlMulti ***", url)
    category = url[1]
    ext = url[2]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url[0], headers=hdr, timeout=(20, 300), verify=False, stream=True)
            r.raise_for_status()

            if r.status_code == requests.codes.ok:
                if ext == "json":
                    json_content = r.json()
                    return category, json_content

                chunk_size = 8192 * 8  # 128 KB

                if output_file:
                    # Save to the specified output file
                    output_dir = os.path.dirname(output_file)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    with open(output_file, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:  # Only write non-empty chunks
                                f.write(chunk)

                    return category, output_file

                else:
                    # Collect chunks into memory and return as content
                    if pythonVer == 2:
                        content = ''
                    else:
                        content = b""

                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:  # Only append non-empty chunks
                            if ext == "text":
                                if pythonVer == 2:
                                    content += chunk.decode('utf-8', errors='ignore')
                                else:
                                    content += chunk.decode('utf-8', errors='ignore').encode('utf-8')
                            else:
                                content += chunk

                    return category, content

        except requests.Timeout as e:
            print("Error message: {}".format(str(e)))
            return category, ""
        except requests.RequestException as e:
            print("Error message: {}".format(str(e)))
            return category, ""


def safeName(name):
    """
    if debugs:
        print("*** safeName ***", name)
        """
    if pythonVer == 2:
        if isinstance(name, str):
            name = name.decode("utf-8", "ignore")
    elif pythonVer == 3:
        if not isinstance(name, str):
            name = str(name)

    # Replace unsafe characters with underscores
    name = re.sub(r'[\'\<\>\:\"\/\\\|\?\*\(\)\[\]]', "_", name)
    name = re.sub(r" ", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")

    # print("*** newname ***", name)

    return name


def purge(my_dir, pattern):
    if debugs:
        print("*** purge ***")
    try:
        for f in os.listdir(my_dir):
            file_path = os.path.join(my_dir, f)
            if os.path.isfile(file_path):
                if re.search(pattern, f):
                    os.remove(file_path)
    except Exception as e:
        print(e)
