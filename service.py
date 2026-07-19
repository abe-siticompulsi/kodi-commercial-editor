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

from resources.lib import beats, keymap, overlay, plexbridge, selfcheck, session, toast, util

_HOME = xbmcgui.Window(10000)
_PROP_DRAFTS = beats.PROP_DRAFTS


class _PlayerWatcher(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._media_path = None
        self._last_pos = 0.0
        self._beat1_fired = set()
        self._pkc_present = False

    def onAVStarted(self):
        _HOME.clearProperty(_PROP_DRAFTS)
        self._last_pos = 0.0
        self._beat1_fired = set()
        self._pkc_present = xbmc.getCondVisibility(
            f"System.AddonIsEnabled({plexbridge.PKC_ID})")
        try:
            self._media_path = self.getPlayingFile()
        except RuntimeError:
            self._media_path = None
            return
        try:
            markers, detail = plexbridge.commercial_markers(self._media_path)
        except Exception as exc:  # noqa: BLE001 — never kill the watcher
            markers, detail = None, f"unexpected: {exc}"
        payload = json.dumps(
            {"file": self._media_path, "detail": detail, "commercials": markers}
        )
        _HOME.setProperty(_PROP_DRAFTS, payload)
        util.log(f"drafts: {payload}", xbmc.LOGINFO)

    def onPlayBackSeek(self, time_ms, seek_offset_ms):
        """The landing detector: any seek matching a draft triggers Beat 2 —
        whoever performed it (our Beat 1, PKC's skip button, a manual jump)."""
        if not self._media_path:
            return
        target = time_ms / 1000.0
        origin = ((time_ms - seek_offset_ms) / 1000.0
                  if seek_offset_ms else self._last_pos)
        self._last_pos = target
        if toast.is_open() or overlay.is_open():
            return
        draft = beats.match_landing(self._media_path, origin, target)
        if draft:
            util.log(f"landing matched draft {draft['start']}-{draft['end']} "
                     f"(origin {origin:.1f})", xbmc.LOGINFO)
            xbmc.executebuiltin(
                f"RunScript({util.ADDON_ID},beat2,{draft['start']},"
                f"{draft['end']},{origin})")

    def tick(self):
        """Once per second from the service loop."""
        if not self._media_path or not self.isPlayingVideo():
            return
        try:
            self._last_pos = self.getTime()
        except RuntimeError:
            return
        if self._pkc_present or toast.is_open() or overlay.is_open():
            return  # PKC's own skip button serves Beat 1
        draft = beats.match_upcoming(self._last_pos)
        if draft and draft["start"] not in self._beat1_fired:
            self._beat1_fired.add(draft["start"])
            xbmc.executebuiltin(
                f"RunScript({util.ADDON_ID},beat1,{draft['start']},"
                f"{draft['end']})")

    def onPlayBackStopped(self):
        self._media_path = None
        session.clear_pending()
        _HOME.clearProperty(_PROP_DRAFTS)

    def onPlayBackEnded(self):
        self._media_path = None
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
    watcher = _PlayerWatcher()
    keymap.sync()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
        watcher.tick()
    session.clear_pending()
    util.log("service stopped", xbmc.LOGINFO)


if __name__ == "__main__":
    main()
