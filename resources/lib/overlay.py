# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""The marking overlay: a small skin-independent dialog drawn over the video.

Primary flow (pause-to-summon): the ad starts, the user pauses, the overlay
appears; clicking the mark button records the timestamp, auto-resumes
playback and closes the overlay. Two pauses + two clicks per break.

M2 additions:
- Nudge row for precise boundary landing (DECISIONS.md #6): seek-emulated
  backward (video decodes forward-only), seeks + native FrameAdvance
  forward. The first nudge pauses playback; the status line shows the
  position after every step.
- "Fix this break": when the playhead is inside a known draft, adopt the
  draft's start as the pending mark so only the end needs re-marking.

Child-simple by design (DECISIONS.md #5)."""

import xbmc
import xbmcgui

from . import beats, session, util

_XML = "script-commercial-editor.xml"

_ACTION_PREVIOUS_MENU = 10
_ACTION_NAV_BACK = 92

_BTN_MARK = 101
_BTN_UNDO = 102
_BTN_CLOSE = 103
_BTN_FRAME = 112
_BTN_ADOPT = 120
_LBL_STATUS = 200

# button id -> seconds
_NUDGES = {110: -1.0, 111: -0.2, 113: 0.2, 114: 1.0}
_NUDGE_LABELS = {110: 32040, 111: 32041, 112: 32042, 113: 32043, 114: 32044}

_HOME = xbmcgui.Window(10000)
_PROP_OPEN = "commercial-editor.overlay.open"


def is_open():
    return _HOME.getProperty(_PROP_OPEN) == "1"


class EditorOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._player = xbmc.Player()
        self._media_path = kwargs.get("media_path", "")
        self._focus_close = kwargs.get("focus_close", False)

    def onInit(self):
        self.getControl(_BTN_UNDO).setLabel(util.L(32003))
        self.getControl(_BTN_CLOSE).setLabel(util.L(32004))
        for control_id, string_id in _NUDGE_LABELS.items():
            self.getControl(control_id).setLabel(util.L(string_id))
        self._draft = None
        now = self._now()
        if now is not None and session.pending_start(self._media_path) is None:
            self._draft = beats.draft_at(now)
        adopt = self.getControl(_BTN_ADOPT)
        if self._draft:
            adopt.setLabel(util.L(32045) % util.fmt_time(self._draft["start"]))
        else:
            adopt.setVisible(False)
        self._refresh(util.L(32013))
        if self._focus_close:
            # Pause-summoned: the pause may not mean "mark" (see default.py),
            # so the safe control gets focus. An explicit summon keeps focus
            # on the mark button.
            self.setFocusId(_BTN_CLOSE)

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

    def _nudge(self, control_id):
        now = self._now()
        if now is None:
            return
        if not xbmc.getCondVisibility("Player.Paused"):
            self._player.pause()  # precision needs a still frame
        if control_id == _BTN_FRAME:
            xbmc.executebuiltin("PlayerControl(FrameAdvance(1))")
        else:
            self._player.seekTime(max(0.0, now + _NUDGES[control_id]))
        xbmc.sleep(150)  # let the player land before reading the position
        position = self._now()
        if position is not None:
            self.getControl(_LBL_STATUS).setLabel(
                util.L(32046) % util.fmt_time(position))

    def _adopt(self):
        session.adopt_start(self._media_path, self._draft["start"])
        self.getControl(_BTN_ADOPT).setVisible(False)
        self._refresh(util.L(32006) % util.fmt_time(self._draft["start"]))

    def onClick(self, control_id):
        if control_id in _NUDGES or control_id == _BTN_FRAME:
            self._nudge(control_id)
        elif control_id == _BTN_ADOPT and self._draft:
            self._adopt()
        elif control_id == _BTN_MARK:
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


def show(media_path, focus_close=False):
    if is_open():
        return
    _HOME.setProperty(_PROP_OPEN, "1")
    try:
        dialog = EditorOverlay(_XML, util.ADDON_PATH, "Default", "1080i",
                               media_path=media_path, focus_close=focus_close)
        dialog.doModal()
        del dialog
    finally:
        _HOME.clearProperty(_PROP_OPEN)
