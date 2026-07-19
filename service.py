# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Background service.

- Pause-to-summon: pausing the video opens the marking overlay (the natural
  reflex when a commercial starts). Silent when prerequisites fail — pausing
  a stream must never nag.
- Draft markers: at playback start, resolves the file to its Plex ratingKey
  and fetches comskip's draft commercial markers (zero-config via PKC).
  Published to a home-window property — the coming Beat-1/Beat-2 flow reads
  them there, and it doubles as a remotely-readable diagnostic.
- Keeps session state honest: clears pending marks and drafts when playback
  stops so they can never leak onto the next video."""

import json

import xbmc
import xbmcgui

from resources.lib import keymap, overlay, plexbridge, selfcheck, session, util

_HOME = xbmcgui.Window(10000)
_PROP_DRAFTS = "commercial-editor.drafts"


class _PlayerWatcher(xbmc.Player):
    def onAVStarted(self):
        _HOME.clearProperty(_PROP_DRAFTS)
        try:
            media_path = self.getPlayingFile()
        except RuntimeError:
            return
        try:
            markers, detail = plexbridge.commercial_markers(media_path)
        except Exception as exc:  # noqa: BLE001 — never kill the watcher
            markers, detail = None, f"unexpected: {exc}"
        payload = json.dumps(
            {"file": media_path, "detail": detail, "commercials": markers}
        )
        _HOME.setProperty(_PROP_DRAFTS, payload)
        util.log(f"drafts: {payload}", xbmc.LOGINFO)

    def onPlayBackStopped(self):
        session.clear_pending()
        _HOME.clearProperty(_PROP_DRAFTS)

    def onPlayBackEnded(self):
        session.clear_pending()
        _HOME.clearProperty(_PROP_DRAFTS)

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
