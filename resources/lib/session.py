# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Marking session state.

A pending start-mark must survive the overlay being closed and reopened, so it
lives in home-window properties keyed to the playing file. The service clears
it when playback stops. Toggle semantics (DECISIONS.md #5): first press marks
the commercial start, second press marks the end and appends the segment to
the EDL sidecar.
"""

import xbmcgui

from . import edl, util

_HOME = xbmcgui.Window(10000)
_PROP_FILE = "commercial-editor.pending.file"
_PROP_START = "commercial-editor.pending.start"

MIN_SEGMENT_SECONDS = 2.0


def pending_start(media_path):
    """Pending start time for this file, or None."""
    if _HOME.getProperty(_PROP_FILE) == media_path:
        value = _HOME.getProperty(_PROP_START)
        if value:
            return float(value)
    return None


def _set_pending(media_path, seconds):
    _HOME.setProperty(_PROP_FILE, media_path)
    _HOME.setProperty(_PROP_START, repr(float(seconds)))


def clear_pending():
    _HOME.clearProperty(_PROP_FILE)
    _HOME.clearProperty(_PROP_START)


def toggle_mark(media_path, seconds):
    """First call: set start mark. Second call: save the segment.

    Returns (saved, message) — `saved` is True when a segment was written.
    """
    start = pending_start(media_path)
    if start is None:
        _set_pending(media_path, seconds)
        return False, util.L(32006) % util.fmt_time(seconds)

    lo, hi = sorted((start, seconds))
    if hi - lo < MIN_SEGMENT_SECONDS:
        # Keep the pending mark: probably an accidental double press.
        return False, util.L(32014)

    if not edl.append(media_path, lo, hi):
        return False, util.L(32012)
    clear_pending()
    util.log(f"saved commercial {lo:.3f}-{hi:.3f} for {media_path}")
    return True, util.L(32005)


def undo(media_path):
    """Cancel the pending mark, or else drop the last saved segment."""
    if pending_start(media_path) is not None:
        clear_pending()
        return util.L(32007)
    removed = edl.pop_last(media_path)
    if removed is None:
        return util.L(32009)
    return util.L(32008) % (util.fmt_time(removed[0]), util.fmt_time(removed[1]))
