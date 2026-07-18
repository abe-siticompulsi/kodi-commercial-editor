# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Bridge to Plex: resolve the playing file to its Plex ratingKey and fetch
draft commercial markers — zero-config when PlexKodiConnect is installed.

Mapping strategy (DECISIONS.md open item 3):
1. The playing item's Kodi library DbId -> PKC's plex.db (`plex_id` IS the
   ratingKey; tables `movie`/`episode` keyed by `kodi_id`).
2. Fallback: file path -> Kodi's MyVideosNNN.db (`files` JOIN `path`) ->
   `kodi_fileid` -> plex.db.

Server + token are borrowed from PKC's own settings (`ipaddress`, `port`,
`https`, `accessToken` — the per-server token PKC itself uses). PKC keeps its
databases in WAL mode, so short-lived read-only connections are safe."""

import os
import re
import sqlite3
import urllib.request
from contextlib import closing
from xml.etree import ElementTree

import xbmc
import xbmcaddon
import xbmcvfs

from . import util

PKC_ID = "plugin.video.plexkodiconnect"


# --- PKC connection (server + token) ---------------------------------------

def pkc_connection():
    """Return (base_url, token) from PKC's settings, or None."""
    if not xbmc.getCondVisibility(f"System.AddonIsEnabled({PKC_ID})"):
        return None
    try:
        addon = xbmcaddon.Addon(PKC_ID)
    except RuntimeError:
        return None
    host = addon.getSetting("ipaddress")
    port = addon.getSetting("port")
    token = addon.getSetting("accessToken")
    if not (host and port and token):
        return None
    scheme = "https" if addon.getSetting("https") == "true" else "http"
    return f"{scheme}://{host}:{port}", token


# --- ratingKey resolution ---------------------------------------------------

def _connect_ro(db_path):
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)


def _plexdb_path():
    path = xbmcvfs.translatePath("special://database/plex.db")
    return path if xbmcvfs.exists(path) else None


def _videodb_path():
    folder = xbmcvfs.translatePath("special://database/")
    best, best_n = None, -1
    _dirs, files = xbmcvfs.listdir(folder)
    for name in files:
        m = re.match(r"MyVideos(\d+)\.db$", name)
        if m and int(m.group(1)) > best_n:
            best_n, best = int(m.group(1)), name
    return os.path.join(folder, best) if best else None


def _playing_dbid():
    """(kodi_dbid, media_type) of the playing library item, or (None, None)."""
    try:
        tag = xbmc.Player().getVideoInfoTag()
    except RuntimeError:
        return None, None
    dbid = tag.getDbId()
    return (dbid if dbid > 0 else None), tag.getMediaType()


def _kodi_fileid(media_path):
    """files.idFile for a full path, via Kodi's video DB (dir + filename)."""
    video_db = _videodb_path()
    if not video_db:
        return None
    sep = "\\" if "\\" in media_path and "/" not in media_path else "/"
    directory, filename = media_path.rsplit(sep, 1)
    directory += sep
    with closing(_connect_ro(video_db)) as conn:
        rows = conn.execute(
            "SELECT f.idFile, p.strPath FROM files f"
            " JOIN path p ON p.idPath = f.idPath WHERE f.strFilename = ?",
            (filename,),
        ).fetchall()
    for file_id, str_path in rows:
        # Kodi occasionally stores triple slashes (PKC normalizes the same way)
        if str_path == directory or str_path.replace("///", "//") == directory:
            return file_id
    return rows[0][0] if len(rows) == 1 else None


def resolve_plex_id(media_path):
    """The Plex ratingKey for the playing file, or None."""
    plex_db = _plexdb_path()
    if not plex_db:
        util.log("plex.db not found — PKC not installed or never synced")
        return None
    with closing(_connect_ro(plex_db)) as conn:
        dbid, media_type = _playing_dbid()
        if dbid and media_type in ("movie", "episode"):
            row = conn.execute(
                f"SELECT plex_id FROM {media_type} WHERE kodi_id = ?", (dbid,)
            ).fetchone()
            if row:
                return row[0]
        file_id = _kodi_fileid(media_path)
        if file_id is None:
            return None
        row = conn.execute(
            "SELECT plex_id FROM movie WHERE kodi_fileid = ?", (file_id,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT plex_id FROM episode WHERE kodi_fileid = ? OR kodi_fileid_2 = ?",
                (file_id, file_id),
            ).fetchone()
        return row[0] if row else None


# --- draft markers ----------------------------------------------------------

def fetch_markers(base_url, token, plex_id):
    """Plex markers for an item: [{'type', 'start', 'end', 'final'}], seconds.

    Raises on network/HTTP errors — callers decide how quiet to be."""
    url = f"{base_url}/library/metadata/{plex_id}?includeMarkers=1"
    request = urllib.request.Request(
        url, headers={"X-Plex-Token": token, "Accept": "application/xml"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        root = ElementTree.parse(response).getroot()
    markers = []
    for marker in root.iter("Marker"):
        markers.append({
            "type": marker.get("type"),
            "start": int(marker.get("startTimeOffset")) / 1000.0,
            "end": int(marker.get("endTimeOffset")) / 1000.0,
            "final": marker.get("final") == "1",
        })
    return markers


def commercial_markers(media_path):
    """One-call convenience: draft commercial segments for the playing file.

    Returns (markers, diagnostic_string). markers is a possibly-empty list,
    or None when resolution/fetch was impossible (no PKC, unmapped file,
    network error — the diagnostic says which)."""
    connection = pkc_connection()
    if not connection:
        return None, "no PKC connection (addon missing or not configured)"
    plex_id = resolve_plex_id(media_path)
    if plex_id is None:
        return None, "file not mapped to a Plex item"
    try:
        markers = fetch_markers(connection[0], connection[1], plex_id)
    except Exception as exc:  # noqa: BLE001 — network layer, keep the addon alive
        return None, f"marker fetch failed: {exc}"
    return [m for m in markers if m["type"] == "commercial"], f"plex_id={plex_id}"
