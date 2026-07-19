# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""The two-beat draft validation flow (DECISIONS.md #7 + open item 5).

Beat 1 — at a draft's start, offer the skip. Only shown when PKC is NOT
present (PKC's own skip button serves Beat 1 otherwise). Clicking Skip seeks
to the draft's end — which fires the landing detector like any other skip.

Beat 2 — at a landing that matches a draft (origin inside the draft, target
near its end — whoever performed the seek), offer Keep / Undo. Only an
explicit Keep writes the EDL. Undo seeks back. Timeout does nothing: the
draft stays a draft.

Shared state between the service (detector) and the RunScript handlers
(dialogs) is the drafts window property published at playback start."""

import json

import xbmc
import xbmcgui

from . import edl, toast, util

_HOME = xbmcgui.Window(10000)
PROP_DRAFTS = "commercial-editor.drafts"

# Matching tolerances (seconds)
ORIGIN_SLACK_BEFORE_START = 2.0   # PKC's button appears right at the start
LANDING_TOLERANCE = 4.0           # target must land near the draft's end
BEAT1_WINDOW = 2.0                # position window after start to offer Beat 1
TOAST_TIMEOUT = 15.0


def drafts():
    """Draft commercial segments for the playing file, from the property."""
    raw = _HOME.getProperty(PROP_DRAFTS)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return data.get("commercials") or []


def _already_in_edl(media_path, draft):
    """True when the EDL already covers this draft (kept earlier)."""
    for start, end, _action in edl.read(media_path):
        if abs(start - draft["start"]) <= LANDING_TOLERANCE and \
           abs(end - draft["end"]) <= LANDING_TOLERANCE:
            return True
    return False


def match_landing(media_path, origin, target):
    """The draft a seek origin→target validates, or None."""
    for draft in drafts():
        if (draft["start"] - ORIGIN_SLACK_BEFORE_START <= origin <= draft["end"]
                and abs(target - draft["end"]) <= LANDING_TOLERANCE
                and not _already_in_edl(media_path, draft)):
            return draft
    return None


def match_upcoming(position):
    """The draft whose start the playhead just entered, or None (Beat 1)."""
    for draft in drafts():
        if draft["start"] <= position <= draft["start"] + BEAT1_WINDOW:
            return draft
    return None


def _fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def beat1(start, end):
    """Offer the skip. Skip = seek to the draft end (fires the detector)."""
    result = toast.show(util.L(32030), util.L(32031), util.L(32004),
                        timeout=TOAST_TIMEOUT)
    if result == "primary":
        try:
            xbmc.Player().seekTime(end)
        except RuntimeError:
            pass


def beat2(media_path, start, end, origin):
    """Validate the landing. ONLY an explicit Keep writes the EDL."""
    message = util.L(32034) % _fmt_duration(end - start)
    result = toast.show(message, util.L(32032), util.L(32033),
                        timeout=TOAST_TIMEOUT)
    if result == "primary":
        if edl.append(media_path, start, end):
            util.notify(util.L(32005))
            util.log(f"kept draft {start:.1f}-{end:.1f} for {media_path}",
                     xbmc.LOGINFO)
        else:
            util.notify(util.L(32012), xbmcgui.NOTIFICATION_WARNING)
    elif result == "secondary":
        try:
            xbmc.Player().seekTime(max(0.0, origin))
        except RuntimeError:
            pass
    # timeout / dismissed: do nothing — the draft stays a draft
