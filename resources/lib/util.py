# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Shared helpers: addon handles, logging, localization, time formatting."""

import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = ADDON.getAddonInfo("path")


def L(string_id):
    """Localized string by id (strings.po)."""
    return ADDON.getLocalizedString(string_id)


def log(msg, level=xbmc.LOGDEBUG):
    if level == xbmc.LOGDEBUG and ADDON.getSettingBool("verbose"):
        level = xbmc.LOGINFO
    xbmc.log(f"[{ADDON_ID}] {msg}", level)


def notify(msg, icon=None):
    import xbmcgui
    xbmcgui.Dialog().notification(ADDON_NAME, msg, icon or xbmcgui.NOTIFICATION_INFO, 4000)


def fmt_time(seconds):
    """Seconds → H:MM:SS.d for on-screen feedback."""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:04.1f}"
