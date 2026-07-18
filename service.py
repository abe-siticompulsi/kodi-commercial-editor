# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Background service.

- Pause-to-summon: pausing the video opens the marking overlay (the natural
  reflex when a commercial starts). Silent when prerequisites fail — pausing
  a stream must never nag.
- Keeps session state honest: clears a pending start-mark when playback
  stops so it can never leak onto the next video.

M1 will grow the draft-marker watcher ("commercial ahead — skip & confirm?")
here."""

import xbmc

from resources.lib import keymap, overlay, selfcheck, session, util


class _PlayerWatcher(xbmc.Player):
    def onPlayBackStopped(self):
        session.clear_pending()

    def onPlayBackEnded(self):
        session.clear_pending()

    def onPlayBackPaused(self):
        if not util.ADDON.getSettingBool("pause_summon"):
            return
        if overlay.is_open():
            return
        try:
            media_path = self.getPlayingFile()
        except RuntimeError:
            return
        ok, _ = selfcheck.check_cached(media_path)
        if ok:
            # Decouple from the player callback thread.
            xbmc.executebuiltin(f"RunScript({util.ADDON_ID},auto)")
        else:
            util.log(f"pause-summon skipped, prerequisites not met: {media_path}")


class _SettingsWatcher(xbmc.Monitor):
    def onSettingsChanged(self):
        keymap.sync()


def main():
    util.log("service started", xbmc.LOGINFO)
    monitor = _SettingsWatcher()
    watcher = _PlayerWatcher()  # noqa: F841 — must stay referenced to receive callbacks
    keymap.sync()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    session.clear_pending()
    util.log("service stopped", xbmc.LOGINFO)


if __name__ == "__main__":
    main()
