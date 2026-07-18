# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Read/write Kodi EDL sidecar files.

Format: one segment per line — `<start> <end> <action>` — where times are
seconds (float) or HH:MM:SS.mmm, and action 3 = commercial break (Kodi
auto-skips it once per playback, rewind-safe). The sidecar shares the media
file's basename: /path/Movie.ts → /path/Movie.edl. All I/O goes through
xbmcvfs so any Kodi-writable VFS protocol (local, SMB, NFS, ...) works.
"""

import re

import xbmcvfs

CUT = 0
MUTE = 1
SCENE_MARKER = 2
COMMERCIAL_BREAK = 3

_LINE = re.compile(r"^\s*([\d:.]+)[ \t]+([\d:.]+)[ \t]+(\d)\s*$")


def edl_path(media_path):
    root, dot, ext = media_path.rpartition(".")
    if dot and "/" not in ext and "\\" not in ext:
        return root + ".edl"
    return media_path + ".edl"


def _parse_time(token):
    if ":" in token:
        parts = [float(p) for p in token.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        h, m, s = parts[-3:]
        return h * 3600 + m * 60 + s
    return float(token)


def read(media_path):
    """Return [(start, end, action), ...]; tolerates missing file and junk lines."""
    path = edl_path(media_path)
    if not xbmcvfs.exists(path):
        return []
    f = xbmcvfs.File(path)
    try:
        content = f.read()
    finally:
        f.close()
    segments = []
    for line in content.splitlines():
        m = _LINE.match(line)
        if m:
            segments.append((_parse_time(m.group(1)), _parse_time(m.group(2)), int(m.group(3))))
    return segments


def write(media_path, segments):
    """Overwrite the sidecar with the given segments (delete it if empty)."""
    path = edl_path(media_path)
    if not segments:
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)
        return True
    data = "".join(f"{s:.3f} {e:.3f} {a}\n" for s, e, a in sorted(segments))
    f = xbmcvfs.File(path, "w")
    try:
        return bool(f.write(data))
    finally:
        f.close()


def append(media_path, start, end, action=COMMERCIAL_BREAK):
    segments = read(media_path)
    segments.append((float(start), float(end), action))
    return write(media_path, segments)


def pop_last(media_path):
    """Remove and return the last segment, or None if the sidecar is empty."""
    segments = read(media_path)
    if not segments:
        return None
    last = segments.pop()
    write(media_path, segments)
    return last
