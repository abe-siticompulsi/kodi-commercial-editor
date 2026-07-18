# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Runnable entry point: open the marking overlay during playback.

Invoked automatically by the service when the video is paused
(RunScript(service.commercial-editor,auto) — errors stay silent), or
manually via Favourites / a keymap / JSON-RPC (errors show a dialog).
Runs the prerequisite self-check first (DECISIONS.md, Prerequisites)."""

import sys

import xbmc
import xbmcgui

from resources.lib import overlay, selfcheck, util


def main():
    auto = len(sys.argv) > 1 and sys.argv[1] == "auto"
    player = xbmc.Player()
    if not player.isPlayingVideo():
        if not auto:
            util.notify(util.L(32010), xbmcgui.NOTIFICATION_WARNING)
        return
    media_path = player.getPlayingFile()
    ok, error = selfcheck.check_cached(media_path)
    if not ok:
        if auto:
            util.log(f"summon refused: {error}")
        else:
            xbmcgui.Dialog().ok(util.ADDON_NAME, error)
        return
    # auto (pause-summoned): focus Close — a pause may not mean "mark".
    # Explicit summon (key/JSON-RPC): focus the mark button — that IS intent.
    overlay.show(media_path, focus_close=auto)


if __name__ == "__main__":
    main()
