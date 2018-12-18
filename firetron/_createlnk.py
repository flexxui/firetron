"""
This module provides the ``create_lnk()`` function for writing Windows
shortcuts (.lnk files).

This module is inspired by the pylnk module (from 2011) by Tim-Christian
Mundt, and would not have been possible without it. The current module
is written for Python3 and has better support for Unicode paths, but
it only deals with writing (not reading) shortcut files.
"""

import os
import re
import time
from io import BytesIO
from struct import pack
from datetime import datetime
from collections import OrderedDict


def create_lnk(
    path,
    target=None,
    arguments=None,
    relative_path=None,
    work_dir=None,
    comment=None,
    icon=None,
    run_mode=None,
):
    """ Create a .lnk file (i.e. a Windows shortcut).
    
    Arguments:
        path (str): The path to the .lnk file to write.
        target (str): The target file. Optional.
        arguments (str): The CLI arguments to call the target with. Optional.
        relative_path (str): The relative path to the target. Optional.
        work_dir (str): The directory to run the target from. Optional.
        comment (str): A descriptive comment for the shortcut. Optional.
        icon (str): The icon to use for the shortcut. Optional.
        run_mode (str): Must be "normal" (default), "maximized" or "minimized".
    """

    if not isinstance(path, str) and path.endswith(".lnk"):
        raise ValueError("Link path must be a string ending with .lnk")

    # Set create, access, modify times
    ctime = datetime.now()
    atime = ctime
    mtime = ctime

    # Determine show mode
    run_modes = {"normal": 1, "maximized": 3, "minimized": 7}
    run_mode = (run_mode or "normal").lower()
    assert run_mode in run_modes, "Invalid run_mode {}".format(run_mode)

    # Determine whether to use Unicode strings in this file
    is_unicode = False
    for x in (comment, relative_path, work_dir, arguments, icon):
        if x:
            try:
                x.encode("ascii")
            except UnicodeError:
                is_unicode = True

    # Define flags. The names used in the dict do not matter; the order does.
    flags = OrderedDict()
    flags["has_target"] = bool(target)
    flags["has_link_info"] = False
    flags["has_comment"] = bool(comment)
    flags["has_relative_path"] = bool(relative_path)
    flags["has_work_dir"] = bool(work_dir)
    flags["has_arguments"] = bool(arguments)
    flags["has_icon"] = bool(icon)
    flags["is_unicode"] = is_unicode
    flags["force_no_link_info"] = True

    # Convert flags to an integer
    flags_int = 0
    for pos, val in enumerate(flags.values()):
        flags_int = flags_int | (int(bool(val)) << pos)

    with open(path, "wb") as f:
        f.write(b"L\x00\x00\x00")
        f.write(b"\x01\x14\x02")
        f.write(b"\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00F")
        f.write(pack("<I", flags_int))
        f.write(pack("<I", 0))  # file attr flags (readonly, directory, etc.)
        _write_windows_time(f, ctime)
        _write_windows_time(f, atime)
        _write_windows_time(f, mtime)
        f.write(pack("<I", 0))  # file size - zero seems to work fine
        f.write(pack("<I", 0))  # icon index
        f.write(pack("<I", run_modes[run_mode]))
        f.write(pack("<BB", 0, 0))  # stub hot key info (two bytes)
        f.write(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")  # reserved
        if target:
            blob = _create_target_id_list(target)
            f.write(pack("<H", len(blob)))
            f.write(blob)
        if flags["has_comment"]:
            _write_str_w_size(f, comment, is_unicode)
        if flags["has_relative_path"]:
            _write_str_w_size(f, relative_path, is_unicode)
        if flags["has_work_dir"]:
            _write_str_w_size(f, work_dir, is_unicode)
        if flags["has_arguments"]:
            _write_str_w_size(f, arguments, is_unicode)
        if flags["has_icon"]:
            _write_str_w_size(f, icon, is_unicode)
        f.write(b"\x00\x00\x00\x00")  # header_size


def _get_path_levels(p):
    dirname, basename = os.path.split(p)
    if basename:
        for level in _get_path_levels(dirname):
            yield level
    yield p


def _create_target_id_list(fullpath):
    """ Encodes the path, in a kinda super-verbose way.
    """

    levels = list(_get_path_levels(fullpath))
    entry_codes = {"folder": 0x31, "file": 0x32}
    entry_codes.update({"folder_uc": 0x35, "file_uc": 0x36})
    blobs = []

    # Absolute path?
    drivedetector = re.compile("(\w)[:/\\\\]*$")
    if drivedetector.match(levels[0].strip()):
        # Root
        blobs.append(b"\x1fP\xe0O\xd0 \xea:i\x10\xa2\xd8\x08\x00+00\x9d")
        # Drive
        driveletter = levels.pop(0).strip().rstrip("/\\:")
        blobs.append(("/" + driveletter + ":\\" + "\x00" * 19).encode())

    # Process all levels
    for path in levels:
        # Prepare
        stats = os.stat(path)
        entry_type = "folder" if os.path.isdir(path) else "file"
        short_name = os.path.basename(path)
        full_name = short_name  # whatever works
        short_name_len = len(short_name) + 1
        try:
            short_name.encode("ascii")
            short_name_unicode = False
            short_name_len += short_name_len % 2  # padding
        except UnicodeError:
            short_name_unicode = True
            short_name_len = short_name_len * 2
            entry_type += "_uc"
        # Write. Unsure what all this does, but it works! Thanks Tim-Christian!
        out = BytesIO()
        out.write(pack("<H", entry_codes[entry_type]))
        out.write(pack("<I", stats.st_size))
        _write_dos_time(out, datetime.fromtimestamp(stats.st_mtime))
        out.write(pack("<H", 0x10))
        if short_name_unicode:
            out.write(short_name.encode("utf-16-le") + b"\x00\x00")
        else:
            val = short_name.encode("cp1252")
            out.write(val + b"\x00")
            if not len(val) % 2:
                out.write(b"\x00")
        out.write(pack("<H", 24 + 2 * len(short_name)))  # some indicator
        out.write(pack("<H", 0x03))
        out.write(pack("<H", 0x04))
        out.write(pack("<H", 0xBEEF))
        _write_dos_time(out, datetime.fromtimestamp(stats.st_ctime))
        _write_dos_time(out, datetime.fromtimestamp(stats.st_atime))
        out.write(pack("<H", 0x14))  # offset for Unicode
        out.write(pack("<H", 0))  # signal that full name is written in Unicode
        out.write(full_name.encode("utf-16-le") + b"\x00\x00")
        out.write(pack("<H", 0x0E + short_name_len))  # some offset
        blobs.append(out.getvalue())

    # Compose all of it
    out = BytesIO()
    for blob in blobs:
        out.write(pack("<H", len(blob) + 2))
        out.write(blob)
    out.write(b"\x00\x00")
    return out.getvalue()


def _write_windows_time(f, dt):
    # Write a Windows time int from a datetime object
    x = int((time.mktime(dt.timetuple()) + 11644473600) * 10000000)
    f.write(pack("<Q", x))


def _write_dos_time(f, dt):
    # Write a dos timestamp from a datetime object
    date = 0
    date = _put_bits(dt.year - 1980, date, 0, 7)
    date = _put_bits(dt.month, date, 7, 4)
    date = _put_bits(dt.day, date, 11, 5)
    f.write(pack("<H", date))
    time = 0
    time = _put_bits(dt.hour, time, 0, 5)
    time = _put_bits(dt.minute, time, 5, 6)
    time = _put_bits(dt.second, time, 11, 5)
    f.write(pack("<H", time))


def _put_bits(bits, target, start, count, length=16):
    return target | bits << (length - start - count)


def _write_str_w_size(f, s, unicode=True):
    # Whether to use Unicode is set via an argument, because several strings
    # in the file must all either be Unicode or not. The size is indeed the
    # number of characters (not bytes).
    f.write(pack("<H", len(s)))
    if unicode:
        f.write(s.encode("utf-16-le"))
    else:
        f.write(s.encode("ascii"))
