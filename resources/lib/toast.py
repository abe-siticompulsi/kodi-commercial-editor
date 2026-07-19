# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""A small two-button toast over the video, with an auto-close timeout.

Used by both beats (DECISIONS.md #7): Beat 1 = "Commercial ahead — skip?"
[Skip / Close], Beat 2 = "Skipped X — keep it?" [Keep / Undo]. Returns
'primary', 'secondary', or None on timeout/dismiss — the timeout MUST be
distinguishable from the secondary action (doing nothing does nothing)."""

import threading

import xbmcgui

from . import util

_XML = "script-commercial-editor-toast.xml"

_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

_BTN_PRIMARY = 101
_BTN_SECONDARY = 102
_LBL_MESSAGE = 200

_HOME = xbmcgui.Window(10000)
_PROP_OPEN = "commercial-editor.toast.open"


def is_open():
    return _HOME.getProperty(_PROP_OPEN) == "1"


class _Toast(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._message = kwargs.get("message", "")
        self._primary = kwargs.get("primary", "")
        self._secondary = kwargs.get("secondary", "")
        self._timeout = kwargs.get("timeout", 15.0)
        self._timer = None
        self.result = None

    def onInit(self):
        self.getControl(_LBL_MESSAGE).setLabel(self._message)
        self.getControl(_BTN_PRIMARY).setLabel(self._primary)
        self.getControl(_BTN_SECONDARY).setLabel(self._secondary)
        self.setFocusId(_BTN_PRIMARY)
        self._timer = threading.Timer(self._timeout, self.close)
        self._timer.start()

    def _finish(self, result):
        self.result = result
        if self._timer:
            self._timer.cancel()
        self.close()

    def onClick(self, control_id):
        if control_id == _BTN_PRIMARY:
            self._finish("primary")
        elif control_id == _BTN_SECONDARY:
            self._finish("secondary")

    def onAction(self, action):
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self._finish(None)


def show(message, primary, secondary, timeout=15.0):
    """Blocking; returns 'primary' | 'secondary' | None (timeout/dismissed)."""
    if is_open():
        return None
    _HOME.setProperty(_PROP_OPEN, "1")
    try:
        dialog = _Toast(_XML, util.ADDON_PATH, "Default", "1080i",
                        message=message, primary=primary, secondary=secondary,
                        timeout=timeout)
        dialog.doModal()
        result = dialog.result
        if dialog._timer:
            dialog._timer.cancel()
        del dialog
        return result
    finally:
        _HOME.clearProperty(_PROP_OPEN)
