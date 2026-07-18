# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Runnable entry point: summon the marking overlay during playback.

Add the addon to Favourites, or bind a key to
RunScript(service.commercial-editor). Runs the prerequisite self-check first
and reports actionable errors (DECISIONS.md, Prerequisites)."""

import xbmc
import xbmcgui

from resources.lib import overlay, selfcheck, util


def main():
    player = xbmc.Player()
    if not player.isPlayingVideo():
        util.notify(util.L(32010), xbmcgui.NOTIFICATION_WARNING)
        return
    media_path = player.getPlayingFile()
    ok, error = selfcheck.check(media_path)
    if not ok:
        xbmcgui.Dialog().ok(util.ADDON_NAME, error)
        return
    overlay.show(media_path)


if __name__ == "__main__":
    main()
