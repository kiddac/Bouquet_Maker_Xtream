#!/usr/bin/python
# -*- coding: utf-8 -*-

from .plugin import playlists_json, cfg, pythonVer, debugs
from . import bouquet_globals as glob

from enigma import eDVBDB
from requests.adapters import HTTPAdapter

import json
import os
import re
import requests
import subprocess
import tempfile
import shutil

hdr = {
    'User-Agent': str(cfg.useragent.value),
    'Accept-Encoding': 'gzip, deflate'
}

if pythonVer == 3:
    superscript_map = str.maketrans(
        '⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ'
        'ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ⁺⁻⁼⁽⁾',
        '0123456789abcdefghijklmnoprstuvwxyz'
        'ABDEGHIJKLMNOPRTUVW+-=()'
    )
    superscript_chars = set(
        '⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ'
        'ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ⁺⁻⁼⁽⁾'
    )


def normalize_superscripts(text):
    return text.translate(superscript_map)


def clean_names(streams, category=None):
    if category in (0, 1, 2):
        field = "category_name"
    elif category == 3:
        field = "name"
    else:
        return streams

    superscript_found = False

    for i, item in enumerate(streams):
        value = item.get(field)
        if isinstance(value, str):
            # Only scan for known superscript chars
            if any(ch in superscript_chars for ch in value):
                item[field] = normalize_superscripts(value)
                superscript_found = True
                glob.superscripts_found = True  # Flag globally

        # If none found yet and global flag not set, stop after 100
        if i >= 99 and not (superscript_found or glob.superscripts_found):
            break

    return streams


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


def downloadXtreamApi(url):
    if debugs:
        print("*** downloadXtreamApi ***", url)
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

    return []


def downloadXtreamApiCategory(url):
    if debugs:
        print("*** downloadXtreamApiCategory ***", url)

    category = url[1]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url[0], headers=hdr, timeout=20, verify=False)
            r.raise_for_status()

            if r.status_code == requests.codes.ok:
                data = r.json()

                if pythonVer == 3:
                    data = clean_names(data, category)

                return category, data

        except Exception as e:
            print("Request failed:", e)
            return category, ""

    return category, ""


def downloadM3U8File(url):
    if debugs:
        print("*** downloadM3U8File ***", url)
    # category = url[1]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url, headers=hdr, timeout=(20, 300), verify=False, stream=True)
            r.raise_for_status()

            if r.status_code == requests.codes.ok:
                # Stream directly into memory
                content_chunks = []
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        content_chunks.append(chunk)

                content = b"".join(content_chunks).decode("utf-8", errors="ignore")

                return content

        except requests.Timeout as e:
            print("Error message: {}".format(str(e)))
            return ""
        except requests.RequestException as e:
            print("Error message: {}".format(str(e)))
            return ""


def downloadM3U8File_wget(url):
    if debugs:
        print("*** downloadM3U8File_wget ***", url)

    tmp_file = None

    try:
        # Create a temporary file for wget output
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file_path = tmp_file.name
        tmp_file.close()

        # Build wget command
        cmd = [
            "wget",
            "--quiet",               # no progress output
            "--timeout=20",          # connect timeout
            "--read-timeout=300",    # read timeout
            "--no-check-certificate",
            "-O", tmp_file_path,
            url
        ]

        # Run wget command
        subprocess.check_call(cmd)

        # Read file content
        with open(tmp_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return content

    except subprocess.CalledProcessError as e:
        print("Error message: {}".format(str(e)))
        return ""

    except Exception as e:
        print("Error message: {}".format(str(e)))
        return ""

    finally:
        if tmp_file and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except Exception:
                pass


def downloadM3U8File_curl_pipe(url):
    # Stream download using curl - returns subprocess for streaming parse
    process = subprocess.Popen(
        ['curl', '-s', '-N', url],  # -N disables buffering
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=8192  # Small buffer for line-by-line processing
    )
    return process


def downloadM3U8File_with_fallback(url):
    if debugs:
        print("*** downloadM3U8File_with_fallback ***", url)

    # Try curl pipe first (streaming)
    try:
        process = downloadM3U8File_curl_pipe(url)
        # Check if process started correctly
        if process and process.poll() is None:
            if debugs:
                print("*** using curl pipe ***")
            return ("curl", process)
        else:
            if debugs:
                print("*** curl pipe failed to start ***")
    except Exception as e:
        print("Curl error: {}".format(str(e)))

    # Try wget next
    try:
        if shutil.which("wget"):
            if debugs:
                print("*** trying wget fallback ***")
            content = downloadM3U8File_wget(url)
            if content:
                if debugs:
                    print("*** wget succeeded ***")
                return ("wget", content)
    except Exception as e:
        print("Wget error: {}".format(str(e)))

    # Final fallback to Python requests
    try:
        if debugs:
            print("*** trying requests fallback ***")
        content = downloadM3U8File(url)
        if content:
            if debugs:
                print("*** requests succeeded ***")
            return ("requests", content)
    except Exception as e:
        print("Requests error: {}".format(str(e)))

    # All failed
    print("*** all download methods failed ***")
    return (None, "")


def safeName(name):
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
