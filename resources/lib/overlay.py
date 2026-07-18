# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""The marking overlay: a small skin-independent dialog drawn over the video.

Primary flow (pause-to-summon): the ad starts, the user pauses, the overlay
appears; clicking the mark button records the timestamp, auto-resumes
playback and closes the overlay. Two pauses + two clicks per break.
Child-simple by design (DECISIONS.md #5)."""

import xbmc
import xbmcgui

from . import session, util

_XML = "script-commercial-editor.xml"

_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

_BTN_MARK = 101
_BTN_UNDO = 102
_BTN_CLOSE = 103
_LBL_STATUS = 200

_HOME = xbmcgui.Window(10000)
_PROP_OPEN = "commercial-editor.overlay.open"


def is_open():
    return _HOME.getProperty(_PROP_OPEN) == "1"


class EditorOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._player = xbmc.Player()
        self._media_path = kwargs.get("media_path", "")

    def onInit(self):
        self.getControl(_BTN_UNDO).setLabel(util.L(32003))
        self.getControl(_BTN_CLOSE).setLabel(util.L(32004))
        self._refresh(util.L(32013))

    def _refresh(self, status):
        marking = session.pending_start(self._media_path) is not None
        self.getControl(_BTN_MARK).setLabel(util.L(32002) if marking else util.L(32001))
        self.getControl(_LBL_STATUS).setLabel(status)

    def _now(self):
        try:
            return self._player.getTime()
        except RuntimeError:  # playback ended under us
            self.close()
            return None

    def _resume_if_paused(self):
        if xbmc.getCondVisibility("Player.Paused"):
            self._player.pause()  # toggles: paused -> playing

    def onClick(self, control_id):
        if control_id == _BTN_MARK:
            now = self._now()
            if now is None:
                return
            _saved, message = session.toggle_mark(self._media_path, now)
            util.notify(message)
            self._resume_if_paused()
            self.close()
        elif control_id == _BTN_UNDO:
            self._refresh(session.undo(self._media_path))
        elif control_id == _BTN_CLOSE:
            # Close only — if the user paused for other reasons, stay paused.
            self.close()

    def onAction(self, action):
        if action.getId() in (_ACTION_PREVIOUS_MENU, _ACTION_NAV_BACK):
            self.close()


def show(media_path):
    if is_open():
        return
    _HOME.setProperty(_PROP_OPEN, "1")
    try:
        dialog = EditorOverlay(_XML, util.ADDON_PATH, "Default", "1080i", media_path=media_path)
        dialog.doModal()
        del dialog
    finally:
        _HOME.clearProperty(_PROP_OPEN)
