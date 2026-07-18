# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Background service: keeps session state honest.

M0 scope: clear a pending start-mark when playback stops so it can never leak
onto the next video. M1 will grow the draft-marker watcher ("commercial ahead
— skip & confirm?") here."""

import xbmc

from resources.lib import session, util


class _PlayerWatcher(xbmc.Player):
    def onPlayBackStopped(self):
        session.clear_pending()

    def onPlayBackEnded(self):
        session.clear_pending()


def main():
    util.log("service started", xbmc.LOGINFO)
    monitor = xbmc.Monitor()
    watcher = _PlayerWatcher()  # noqa: F841 — must stay referenced to receive callbacks
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    session.clear_pending()
    util.log("service stopped", xbmc.LOGINFO)


if __name__ == "__main__":
    main()
