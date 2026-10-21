#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Save and restore the order of Enigma2 bouquet references."""

from collections import deque
import io
import json
import os
import re


BOUQUETS_TV = "/etc/enigma2/bouquets.tv"
ORDER_FILENAME = "bouquets_tv_order.json"
BOUQUET_RE = re.compile(r'FROM BOUQUET\s+"([^"]+)"')


def _bouquet_name(line):
    """Return the referenced bouquet filename, or None for a non-reference line."""
    if not line.startswith("#SERVICE "):
        return None

    match = BOUQUET_RE.search(line)
    if match:
        return match.group(1)

    return None


def _read_order(bouquet_path):
    """Return the referenced bouquet filenames in their current order."""
    order = []
    with io.open(bouquet_path, "r", encoding="utf-8") as bouquet_file:
        for line in bouquet_file:
            name = _bouquet_name(line)
            if name is not None:
                order.append(name)
    return order


def _atomic_replace(source_path, target_path):
    """Atomically replace a file on both Python 2 boxes and Python 3 hosts."""
    replace = getattr(os, "replace", os.rename)
    replace(source_path, target_path)


def _grouped_bouquet_path(grouped_bouquet, bouquets_path):
    """Resolve a grouped parent filename within the Enigma2 bouquet directory."""
    # Callers supply generated filenames, but basename also prevents a malformed
    # value from making the snapshot read or write outside the bouquet directory.
    filename = os.path.basename(grouped_bouquet)
    return filename, os.path.join(os.path.dirname(bouquets_path), filename)


def _load_saved_files(order_path, bouquets_path):
    """Load an existing snapshot and normalise older versions."""
    if not os.path.isfile(order_path):
        return {}

    with open(order_path, "rb") as order_file:
        data = json.loads(order_file.read().decode("utf-8"))

    if not isinstance(data, dict):
        return {}

    if data.get("version") == 1:
        files = {
            os.path.basename(bouquets_path): data.get("bouquets", [])
        }
    else:
        files = data.get("files", {})

    return files if isinstance(files, dict) else {}


def _write_saved_files(order_path, files):
    """Write a version 2 snapshot atomically."""
    temporary_path = order_path + ".tmp"
    data = {
        "version": 2,
        "files": files
    }
    serialized_data = json.dumps(data, indent=4, ensure_ascii=False)

    try:
        with open(temporary_path, "wb") as order_file:
            order_file.write(serialized_data.encode("utf-8"))
            order_file.write(b"\n")
        _atomic_replace(temporary_path, order_path)
    except Exception:
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
        except Exception:
            pass
        raise


def save_bouquet_order(config_directory, grouped_bouquets=None, bouquets_path=BOUQUETS_TV):
    """Persist top-level and grouped-parent bouquet ordering before a rebuild."""
    order_path = os.path.join(config_directory, ORDER_FILENAME)

    try:
        if not os.path.isdir(config_directory):
            os.makedirs(config_directory)

        # A single-provider build only knows about that provider's grouped
        # bouquet. Start with the previous snapshot so its update cannot erase
        # the saved sub-bouquet orders belonging to every other provider.
        files = _load_saved_files(order_path, bouquets_path)
        files[os.path.basename(bouquets_path)] = _read_order(bouquets_path)

        # Only inspect explicitly supplied grouped parent files. Scanning every
        # generated bouquet would needlessly read files containing all channels.
        saved_grouped_bouquets = set()
        for grouped_bouquet in grouped_bouquets or []:
            filename, grouped_path = _grouped_bouquet_path(grouped_bouquet, bouquets_path)
            if filename in saved_grouped_bouquets or not os.path.isfile(grouped_path):
                continue
            files[filename] = _read_order(grouped_path)
            saved_grouped_bouquets.add(filename)

        _write_saved_files(order_path, files)
        return True
    except Exception as error:
        print("BouquetMakerXtream: unable to save bouquet order: {}".format(error))
        return False


def _provider_bouquet(filename, provider_name):
    """Return whether a generated bouquet belongs to one provider."""
    user_base = "userbouquet.bouquetmakerxtream_"
    if filename == user_base + provider_name + ".tv":
        return True

    for bouquet_type in ("live_", "vod_", "series_"):
        provider_prefix = "bouquetmakerxtream_" + bouquet_type + provider_name + "_"
        if filename.startswith("userbouquet." + provider_prefix):
            return True
        if filename.startswith("subbouquet." + provider_prefix):
            return True

    return False


def clean_bouquet_order(config_directory, provider_names=None, remove_all=False,
                        bouquets_path=BOUQUETS_TV):
    """Remove deleted provider references from the persisted order snapshot."""
    order_path = os.path.join(config_directory, ORDER_FILENAME)

    try:
        if not os.path.isfile(order_path):
            return False

        provider_names = [str(name) for name in (provider_names or []) if name]
        files = _load_saved_files(order_path, bouquets_path)
        main_filename = os.path.basename(bouquets_path)

        def should_remove(filename):
            if remove_all:
                return "bouquetmakerxtream" in filename
            return any(_provider_bouquet(filename, name) for name in provider_names)

        cleaned_files = {}
        for filename, saved_order in files.items():
            # Keep the main index itself, but remove deleted references from it.
            if filename != main_filename and should_remove(filename):
                continue

            if isinstance(saved_order, list):
                saved_order = [
                    name for name in saved_order
                    if not should_remove(name)
                ]
            cleaned_files[filename] = saved_order

        _write_saved_files(order_path, cleaned_files)
        return True
    except Exception as error:
        print("BouquetMakerXtream: unable to clean bouquet order: {}".format(error))
        return False


def _restore_file_order(bouquet_path, saved_order):
    """Restore reference order in one bouquet index file."""
    if not isinstance(saved_order, list) or not os.path.isfile(bouquet_path):
        return False

    with io.open(bouquet_path, "r", encoding="utf-8", errors="replace") as bouquet_file:
        lines = bouquet_file.readlines()

    current_entries = []
    for index, line in enumerate(lines):
        name = _bouquet_name(line)
        if name is not None:
            current_entries.append((index, name, line))

    # Queues preserve duplicate references without the O(n) cost of pop(0).
    entries_by_name = {}
    for entry in current_entries:
        entries_by_name.setdefault(entry[1], deque()).append(entry)

    ordered_entries = []
    used_indexes = set()
    for name in saved_order:
        entries = entries_by_name.get(name)
        if entries:
            entry = entries.popleft()
            ordered_entries.append(entry)
            used_indexes.add(entry[0])

    # New entries retain their generated order after all matching old entries.
    for entry in current_entries:
        if entry[0] not in used_indexes:
            ordered_entries.append(entry)

    ordered_lines = [entry[2] for entry in ordered_entries]
    ordered_line_index = 0
    output = []

    # Replace only bouquet-reference slots, preserving #NAME and other lines.
    for line in lines:
        if _bouquet_name(line) is not None:
            output.append(ordered_lines[ordered_line_index])
            ordered_line_index += 1
        else:
            output.append(line)

    temporary_path = bouquet_path + ".bmxorder.tmp"
    try:
        with io.open(temporary_path, "w", encoding="utf-8") as bouquet_file:
            bouquet_file.writelines(output)
        _atomic_replace(temporary_path, bouquet_path)
    except Exception:
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
        except Exception:
            pass
        raise

    return True


def restore_bouquet_order(config_directory, bouquets_path=BOUQUETS_TV):
    """Restore matching references and leave newly created ones at the bottom."""
    order_path = os.path.join(config_directory, ORDER_FILENAME)

    try:
        if not os.path.isfile(order_path):
            return False

        files = _load_saved_files(order_path, bouquets_path)

        bouquet_directory = os.path.dirname(bouquets_path)
        main_filename = os.path.basename(bouquets_path)
        restored = False

        # Restore grouped parents first and the top-level index last.
        filenames = [name for name in files if name != main_filename]
        if main_filename in files:
            filenames.append(main_filename)

        for filename in filenames:
            safe_filename = os.path.basename(filename)
            if not safe_filename or safe_filename != filename:
                continue
            target_path = os.path.join(bouquet_directory, safe_filename)
            restored = _restore_file_order(target_path, files[filename]) or restored

        return restored
    except Exception as error:
        print("BouquetMakerXtream: unable to restore bouquet order: {}".format(error))
        return False
