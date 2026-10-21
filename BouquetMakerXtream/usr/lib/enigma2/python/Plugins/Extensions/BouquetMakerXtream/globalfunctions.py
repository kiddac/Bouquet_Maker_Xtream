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

hdr = {
    'User-Agent': str(cfg.useragent.value)
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
    response = []

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url, headers=hdr, timeout=(10, 20), verify=False)
            r.raise_for_status()

            # Get Content-Type from headers
            content_type = r.headers.get('Content-Type', '')

            # Handle JSON content directly
            if 'application/json' in content_type:
                try:
                    response = r.json()

                except ValueError as e:
                    print("Error decoding JSON:", e, url)
                    response = []

            # Handle text/html content
            elif 'text/html' in content_type:
                try:
                    # Attempt to parse the HTML body as JSON
                    response_text = r.text
                    response = json.loads(response_text)

                except ValueError as e:
                    print("Error decoding JSON from HTML content:", e, url)
                    response = []

            else:
                print("Final response is non-JSON content:", r.url)
                response = []

        except Exception as e:
            print("Request failed:", e)
            response = []

    return response


def downloadXtreamApiCategory(url):
    if debugs:
        print("*** downloadXtreamApiCategory ***", url)

    category = url[1]
    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    response = []

    with requests.Session() as http:
        http.mount("http://", adapter)
        http.mount("https://", adapter)

        try:
            r = http.get(url[0], headers=hdr, timeout=(10, 20), verify=False)
            r.raise_for_status()

            # Get Content-Type from headers
            content_type = r.headers.get('Content-Type', '')

            # Handle JSON content directly
            if 'application/json' in content_type:
                try:
                    response = r.json()

                except ValueError as e:
                    print("Error decoding JSON:", e, url)
                    response = []

            # Handle text/html content
            elif 'text/html' in content_type:
                try:
                    # Attempt to parse the HTML body as JSON
                    response_text = r.text
                    response = json.loads(response_text)

                except ValueError as e:
                    print("Error decoding JSON from HTML content:", e, url)
                    response = []

            else:
                print("Final response is non-JSON content:", r.url)
                response = []

        except Exception as e:
            print("Request failed:", e)
            response = []

    if pythonVer == 3:
        response = clean_names(response, category)

    return category, response


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


def _isValidBmxBouquet(filename, valid_names):
    """Return True when a generated bouquet belongs to a current playlist."""
    user_prefix = "userbouquet.bouquetmakerxtream_"
    sub_prefix = "subbouquet.bouquetmakerxtream_"

    if filename.startswith(user_prefix) and filename.endswith(".tv"):
        remainder = filename[len(user_prefix):-3]
        if remainder in valid_names:
            return True
    elif filename.startswith(sub_prefix) and filename.endswith(".tv"):
        remainder = filename[len(sub_prefix):-3]
    else:
        return False

    for bouquet_type in ("live_", "vod_", "series_"):
        if not remainder.startswith(bouquet_type):
            continue
        provider_and_category = remainder[len(bouquet_type):]
        return any(
            provider_and_category.startswith(name + "_")
            for name in valid_names
        )

    return False


def _isBmxBouquet(filename):
    return (
        filename.startswith("userbouquet.bouquetmakerxtream_") or
        filename.startswith("subbouquet.bouquetmakerxtream_")
    ) and filename.endswith(".tv")


def reconcileGeneratedArtifacts(playlists, bouquet_directory="/etc/enigma2",
                                epg_directory="/etc/epgimport"):
    """Remove generated bouquet and EPG artifacts for deleted playlist names."""
    import xml.etree.ElementTree as ET

    valid_names = set()
    for playlist in playlists or []:
        try:
            name = safeName(playlist["playlist_info"]["name"])
            if name:
                valid_names.add(name)
        except Exception:
            continue

    changed = False

    # Remove generated bouquet files which no longer belong to a playlist.
    if os.path.isdir(bouquet_directory):
        for filename in os.listdir(bouquet_directory):
            if not _isBmxBouquet(filename):
                continue
            if _isValidBmxBouquet(filename, valid_names):
                continue
            try:
                os.remove(os.path.join(bouquet_directory, filename))
                changed = True
            except OSError as error:
                print("BouquetMakerXtream: unable to remove %s: %s" % (filename, error))

        # Clean top-level and grouped bouquet references after stale files have
        # been removed. This also removes dangling references from interrupted
        # or incomplete builds.
        reference_files = [os.path.join(bouquet_directory, "bouquets.tv")]
        reference_files.extend(
            os.path.join(bouquet_directory, filename)
            for filename in os.listdir(bouquet_directory)
            if filename.startswith("userbouquet.bouquetmakerxtream_") and
            filename.endswith(".tv") and
            _isValidBmxBouquet(filename, valid_names)
        )

        bouquet_reference = re.compile(r'FROM BOUQUET\s+"([^"]+)"')
        for reference_file in reference_files:
            if not os.path.isfile(reference_file):
                continue
            try:
                with open(reference_file, "r") as bouquet_file:
                    lines = bouquet_file.readlines()

                output = []
                file_changed = False
                for line in lines:
                    match = bouquet_reference.search(line)
                    if match:
                        target = os.path.basename(match.group(1))
                        target_path = os.path.join(bouquet_directory, target)
                        if _isBmxBouquet(target) and (
                                not _isValidBmxBouquet(target, valid_names) or
                                not os.path.isfile(target_path)):
                            file_changed = True
                            continue
                    output.append(line)

                if file_changed:
                    with open(reference_file, "w") as bouquet_file:
                        bouquet_file.writelines(output)
                    changed = True
            except (IOError, OSError) as error:
                print("BouquetMakerXtream: unable to clean %s: %s" % (reference_file, error))

    if not os.path.isdir(epg_directory):
        return changed

    # Remove obsolete per-provider channel files.
    channel_prefix = "bouquetmakerxtream."
    channel_suffix = ".channels.xml"
    valid_channel_files = set(
        channel_prefix + name + channel_suffix for name in valid_names
    )
    for filename in os.listdir(epg_directory):
        if not (filename.startswith(channel_prefix) and filename.endswith(channel_suffix)):
            continue
        if filename in valid_channel_files:
            continue
        try:
            os.remove(os.path.join(epg_directory, filename))
            changed = True
        except OSError as error:
            print("BouquetMakerXtream: unable to remove %s: %s" % (filename, error))

    # Remove stale sources from the correct parent element. The previous code
    # attempted root.remove(source), although source is nested under sourcecat.
    source_file = os.path.join(epg_directory, "bouquetmakerxtream.sources.xml")
    if os.path.isfile(source_file):
        try:
            tree = ET.parse(source_file, parser=ET.XMLParser(encoding="utf-8"))
            root = tree.getroot()
            xml_changed = False

            for parent in root.iter():
                is_bmx_category = parent.get("sourcecatname") == "BouquetMakerXtream EPG"
                for source in list(parent):
                    if source.tag != "source":
                        continue

                    channels = os.path.basename(source.get("channels", ""))
                    is_bmx_source = is_bmx_category or (
                        channels.startswith(channel_prefix) and
                        channels.endswith(channel_suffix)
                    )
                    if not is_bmx_source:
                        continue

                    description_node = source.find("description")
                    description = ""
                    if description_node is not None and description_node.text:
                        description = description_node.text.strip()

                    if description not in valid_names or channels not in valid_channel_files:
                        parent.remove(source)
                        xml_changed = True

            if xml_changed:
                tree.write(source_file, encoding="utf-8", xml_declaration=True)
                changed = True
        except Exception as error:
            print("BouquetMakerXtream: unable to clean EPG sources: %s" % error)

    return changed


def downloadM3U8Lines(url):
    if debugs:
        print("*** downloadM3U8Lines ***", url)

    retries = 0
    adapter = HTTPAdapter(max_retries=retries)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    response = None

    try:
        response = http.get(
            url,
            headers=hdr,
            timeout=(20, 300),
            verify=False,
            stream=True
        )
        response.raise_for_status()

        if response.status_code != requests.codes.ok:
            return

        for line in response.iter_lines(chunk_size=256 * 1024, decode_unicode=False):
            if line:
                if isinstance(line, bytes):
                    line = line.decode("utf-8", "ignore")
                yield line

    except MemoryError:
        print("downloadM3U8Lines: MemoryError - insufficient memory")

    except requests.Timeout as e:
        print("Error message: {}".format(str(e)))

    except requests.RequestException as e:
        print("Error message: {}".format(str(e)))

    finally:
        try:
            if response:
                response.close()
        except:
            pass
        try:
            http.close()
        except:
            pass
