# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Runnable entry point: open the marking overlay during playback.

Invoked automatically by the service when the video is paused
(RunScript(service.commercial-editor,auto) — errors stay silent), or
manually via Favourites / a keymap / JSON-RPC (errors show a dialog).
Runs the prerequisite self-check first (DECISIONS.md, Prerequisites).

The 'diag' argument runs the Plex-bridge diagnostic instead: it resolves
the playing file to its ratingKey, fetches draft commercial markers, and
publishes the result (never the token) as a home-window property so it can
be read remotely via JSON-RPC."""

import json
import sys

import xbmc
import xbmcgui

from resources.lib import overlay, selfcheck, util

_PROP_DIAG = "commercial-editor.diag"


def diag():
    from resources.lib import plexbridge
    player = xbmc.Player()
    result = {"playing": player.isPlayingVideo()}
    if result["playing"]:
        media_path = player.getPlayingFile()
        result["file"] = media_path
        result["pkc_connection"] = plexbridge.pkc_connection() is not None
        markers, detail = plexbridge.commercial_markers(media_path)
        result["detail"] = detail
        result["commercials"] = markers
    payload = json.dumps(result)
    xbmcgui.Window(10000).setProperty(_PROP_DIAG, payload)
    util.log(f"diag: {payload}", xbmc.LOGINFO)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "diag":
        diag()
        return
    if arg == "beat1":
        from resources.lib import beats
        beats.beat1(float(sys.argv[2]), float(sys.argv[3]))
        return
    if arg == "beat2":
        from resources.lib import beats
        player = xbmc.Player()
        if player.isPlayingVideo():
            beats.beat2(player.getPlayingFile(), float(sys.argv[2]),
                        float(sys.argv[3]), float(sys.argv[4]))
        return
    auto = arg == "auto"
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
