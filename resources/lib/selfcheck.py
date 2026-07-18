# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Prerequisite self-check (DECISIONS.md): the addon must fail with an
actionable message, not silently.

1. Kodi must be playing a real file (EDL is resolved against the file path,
   so plugin/http streams can never work).
2. The media directory must be writable through Kodi's VFS (the sidecar is
   written next to the recording).
"""

import re

import xbmcgui
import xbmcvfs

from . import util

_HOME = xbmcgui.Window(10000)
_PROP_CHECK_FILE = "commercial-editor.check.file"
_PROP_CHECK_OK = "commercial-editor.check.ok"

_NON_DIRECT = ("plugin://", "http://", "https://", "pvr://", "upnp://", "videodb://", "pipe://")
_PROBE_NAME = ".commercial-editor.probe"


def is_direct_path(media_path):
    return bool(media_path) and not media_path.lower().startswith(_NON_DIRECT)


def media_dir(media_path):
    return re.split(r"[/\\][^/\\]+$", media_path)[0]


def dir_writable(media_path):
    """Probe-write a tiny file next to the media, then remove it."""
    probe = media_dir(media_path) + "/" + _PROBE_NAME
    f = xbmcvfs.File(probe, "w")
    try:
        ok = bool(f.write("probe"))
    finally:
        f.close()
    if ok:
        xbmcvfs.delete(probe)
    return ok


def check(media_path):
    """Return (ok, localized_error_message)."""
    if not media_path:
        return False, util.L(32010)
    if not is_direct_path(media_path):
        util.log(f"not a direct path: {media_path}")
        return False, util.L(32011)
    if not dir_writable(media_path):
        util.log(f"media dir not writable: {media_dir(media_path)}")
        return False, util.L(32012)
    return True, ""


def check_cached(media_path):
    """Like check(), but probe each file only once — the pause-summon path
    runs on every pause and must not spam probe writes onto the share."""
    if media_path and _HOME.getProperty(_PROP_CHECK_FILE) == media_path:
        return _HOME.getProperty(_PROP_CHECK_OK) == "1", ""
    ok, message = check(media_path)
    if media_path:
        _HOME.setProperty(_PROP_CHECK_FILE, media_path)
        _HOME.setProperty(_PROP_CHECK_OK, "1" if ok else "0")
    return ok, message
