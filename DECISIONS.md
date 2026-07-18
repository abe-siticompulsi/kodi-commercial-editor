# Design decisions

A Kodi service addon to **add / edit / delete / fix commercial timestamps** on video
recordings, from inside Kodi. An automatic commercial detector (e.g. Plex DVR's
embedded comskip) provides an imprecise — sometimes empty — draft; a human corrects it
during playback, and Kodi then auto-skips the verified segments via an EDL sidecar.

---

## Prerequisites

For the addon to work, the user's setup must satisfy:

1. **Kodi must play the actual media file** (local path or network share), not a
   transcoded/proxied stream — EDL sidecars are resolved against the real file path.
   Examples: native Kodi library, or PlexKodiConnect with Direct Paths enabled.
2. **The media source must be writable by Kodi** — the addon writes `.edl` sidecar
   files next to the recordings. Any protocol Kodi's VFS can write to qualifies
   (local disk, SMB, NFS, …).
3. *(Optional — draft markers only)* **A reachable Plex Media Server + API token**, to
   fetch comskip's draft commercial markers. Without Plex, the addon still works as a
   pure manual marker editor.

The addon verifies 1 and 2 at first run / playback start and reports actionable
errors instead of failing silently (see Build plan, M0).

## Architecture

| # | Decision | Reasoning |
|---|---|---|
| 1 | **Write target = EDL sidecar** — action `3` (commercial break), same basename as the media file, times in seconds or `HH:MM:SS.mmm` | Kodi auto-skips EDL commercial segments silently (treated like chapters), they coexist without conflict with Plex markers (which Plex↔Kodi bridges surface only as an optional skip *button*), survive Plex re-analysis, and require no DB access. |
| 2 | **Plex = read-only draft source** via `GET /library/metadata/{ratingKey}?includeMarkers=1` (offsets in ms, `type="commercial"`) | Plex has no working write API for markers (CRUD endpoints return 400); direct SQLite writes are unsupported, need PMS stopped, and are wiped on re-analysis. Read the draft, never write back. |
| 3 | **Front-end = Kodi Python service addon** | Editing must happen where playback happens. Everything runs through Kodi's own APIs (`xbmc.Player`, `xbmcvfs`, JSON-RPC), so the addon is agnostic to how the library got into Kodi. |

## UX

| # | Decision | Reasoning |
|---|---|---|
| 4 | **Live-marking during playback** (v1); dedicated editor screen deferred | The pain occurs while watching; the fix must be one gesture away. Also far less Kodi-UI code than a timeline editor. |
| 5 | **On-screen overlay dialog** (Up Next-style custom WindowXMLDialog), not a hardware keymap | Skin-independent, operable with any pointer or remote, and simple enough for a child: one gesture, zero menus. Buttons: mark start / mark end / undo. |
| 6 | **Precision = addon-built nudge** (±1 s and ±0.2 s steps via JSON-RPC `Player.Seek` millisecond precision) | Kodi has no native frame-step; programmatic seeking makes it unnecessary. ±0.2 s ≈ frame-precision for ad boundaries, and EDL action 3 is rewind-safe if a cut is slightly greedy. |
| 7 | **Seed strategy = verified-only, validated in two beats.** Invariant: *nothing enters the EDL that the user hasn't experienced and explicitly accepted.* | Automatic detection is imprecise by definition; a silent wrong jump mid-movie is worse than an unpressed button. Confirming a draft *before* the skip would bless boundaries the user hasn't seen — so validation follows what the eye can verify at each moment. **Beat 1 — at the draft's start:** offer the skip ("Commercial ahead — skip?"); clicking implicitly verifies the start (an ad is visibly playing) and jumps *provisionally*, in-session only. **Beat 2 — at the landing:** the user now sees the end boundary, the part detection most often gets wrong; a toast offers "Keep / Undo". Only an explicit **Keep** writes the EDL. Doing nothing does nothing — the draft stays a draft and offers itself again next playback. Undo seeks back, no write. |

## Build plan

- **M0 — the spine:** manual mark → EDL write → verified auto-skip on next play.
  No Plex API. Includes the **prerequisite self-check** (is this a real file path?
  is the directory writable?) with clear, actionable error messages.
- **M1 — the brains:** playing-file ↔ Plex ratingKey mapping, draft-marker fetch,
  the "skip & confirm?" popup. **v1 = M0 + M1.**
- **M2 — deferred:** nudge-adjust of draft boundaries. v1 handles a bad boundary by
  dismissing the draft and re-marking by hand; M2 gets built only if that proves
  annoying in practice.

## Open items

| # | Item | Status |
|---|---|---|
| 1 | Overlay-summon mechanism mid-playback | **Resolved: pause-to-summon.** Field-testing killed the alternatives (favourites is unreachable during fullscreen video without a dedicated key; default keymaps conflict — `e` is live TV). Pausing is the natural reflex when an ad starts, works with every remote, needs zero setup. The service listens for `onPlayBackPaused`; marking auto-resumes playback. Keymap/JSON-RPC remain as manual fallbacks; a settings toggle disables the pause hook. |
| 2 | `Player.Seek` real-world ms granularity | Verify empirically during M0. M2 nudge design (refined): the addon seeks at its own granularity and never relies on Kodi's skip-steps (10 s default — navigation, not precision). Backward = seek-emulated "go back a little" (−1 s coarse, −0.2 s fine; video codecs decode forward-only, so no native back-step exists). Forward = +0.2 s / +1 s seeks plus native `PlayerControl(FrameAdvance(n))` for frame-perfect landing while paused. Expected flow: pause near the boundary → back a little → frame-forward → mark. |
| 3 | Kodi-file ↔ Plex-ratingKey mapping | Design at M1. Candidate strategies: PlexKodiConnect's local DB (stores Plex IDs) when present; fallback = match by file path/name via the Plex API. Must not hard-depend on any specific bridge. |
| 4 | Configurable summon key | Backlog. The managed keymap hardcodes `e` (fullscreen video + video OSD); a settings option should let the user pick the key. |
| 5 | Beat-1 coexistence with PKC's skip button | M1. PlexKodiConnect already shows its own skip button at Plex commercial markers — our Beat-1 popup would duplicate it. Detect PKC via `System.AddonIsEnabled(plugin.video.plexkodiconnect)`. Candidate design: when PKC is present, suppress our Beat-1 popup and instead detect the skip via `Player.onPlayBackSeek` (a jump from ≈draft start to ≈draft end is a Beat 1, whoever performed it — our popup, PKC's button, or a manual seek), then fire the Beat-2 Keep/Undo toast on the landing. One skip UI, our validation layer on top. |

## Accepted risks

- **EDL is path-based:** if recordings move or get renamed, sidecars must travel too.
- **First watch sees the ads** (at least their starts) — inherent to human verification.
- **Bridge dependency is soft:** the draft-marker *button* comes from the user's
  Plex↔Kodi bridge, but the addon's own loop (API read → EDL write → Kodi native
  skip) works regardless of which bridge — or none — is in use.
