# Commercial Editor (Kodi addon)

Fix commercial timestamps **from inside Kodi**, while you watch. Automatic
commercial detection (e.g. Plex DVR's embedded comskip) is never 100% right —
sometimes it's off by seconds, sometimes it finds nothing at all. This addon
lets you mark or correct the breaks with a simple on-screen overlay; verified
segments are written to an **EDL sidecar** next to the recording, which Kodi
then **auto-skips on every future playback**. Nothing auto-skips that a human
hasn't confirmed.

See [DECISIONS.md](DECISIONS.md) for the full design rationale.

## Prerequisites

1. **Kodi must play the actual media file** (local path or network share such
   as SMB/NFS), not a transcoded/proxied stream — EDL sidecars are resolved
   against the real file path. Examples: native Kodi library, or
   PlexKodiConnect with *Direct Paths* enabled.
2. **The media source must be writable by Kodi** — the addon writes `.edl`
   files next to the recordings.
3. *(Optional, planned for M1)* a reachable Plex Media Server + API token, to
   seed the editor with comskip's draft markers.

The addon checks 1 and 2 when summoned and tells you exactly what's wrong
instead of failing silently.

## Status

**M0 — the spine** (in progress): manual mark → EDL write → auto-skip on next
play, plus the prerequisite self-check.

Roadmap: **M1** adds Plex draft markers and a "commercial ahead — skip &
confirm?" popup (v1 = M0+M1). **M2** adds fine boundary adjustment (±0.2 s
nudge). No addon icon/fanart yet.

## Install (development)

1. Copy (or symlink) this folder into Kodi's addon directory as
   `service.commercial-editor`, or zip it and use *Install from zip file*.
2. Enable it under *Add-ons → My add-ons → Services*.

## Usage

**Just pause.** When a commercial starts, pause the video — the editor
overlay appears. Click **Commercial starts here**: playback resumes by
itself. When the commercial ends, pause again and click **Commercial ends
here**: the segment is saved and playback resumes. Two pauses, two clicks
per break. **Undo** removes the pending mark or the last saved segment;
**Close** dismisses the overlay and leaves the video paused (pausing for
other reasons stays possible — the overlay never resumes on its own).

Manual summoning also works: the addon installs its own keymap — press
**`e`** during fullscreen video *or while the video OSD is up* (handy after
fine-seeking to a boundary with the OSD). When summoned this way the mark
button is focused; when auto-opened by a pause, **Close** is focused (a pause
may not mean "mark"). Both the pause hook and the keymap can be disabled in
the addon settings (disabling the keymap removes the file again). For a
different key, turn the managed keymap off and drop your own file in
`special://profile/keymaps/`. JSON-RPC works too:
`{"jsonrpc":"2.0","method":"Addons.ExecuteAddon","params":{"addonid":"service.commercial-editor"},"id":1}`

Note: Kodi loads EDL sidecars when playback starts, so a segment saved during
the current session takes effect from the *next* playback.

## License

[GPL-3.0-or-later](LICENSE)
