# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 abe-siticompulsi and contributors
"""Self-installing keymap.

Kodi has no declarative way for an addon to ship key bindings, so the service
writes (and manages) its own keymap file in the live profile and reloads
keymaps. special://profile/ always resolves to the profile Kodi is actually
running (native, Flatpak, Android, ...), so no path guessing is involved.
Disabling the setting removes the file again."""

import xbmc
import xbmcvfs

from . import util

_PATH = "special://profile/keymaps/commercial-editor.gen.xml"

_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated and managed by service.commercial-editor (addon settings).
     Manual edits will be overwritten. -->
<keymap>
  <fullscreenvideo>
    <keyboard>
      <e>RunScript(service.commercial-editor)</e>
    </keyboard>
  </fullscreenvideo>
  <!-- Also while the OSD is up: the natural flow is fine-seeking to the
       boundary with the OSD, then summoning the editor right there. -->
  <videoosd>
    <keyboard>
      <e>RunScript(service.commercial-editor)</e>
    </keyboard>
  </videoosd>
</keymap>
"""


def _read():
    if not xbmcvfs.exists(_PATH):
        return None
    f = xbmcvfs.File(_PATH)
    try:
        return f.read()
    finally:
        f.close()


def sync():
    """Make the installed keymap match the setting; reload only on change."""
    want = util.ADDON.getSettingBool("install_keymap")
    current = _read()
    if want and current != _CONTENT:
        xbmcvfs.mkdirs("special://profile/keymaps")
        f = xbmcvfs.File(_PATH, "w")
        try:
            ok = bool(f.write(_CONTENT))
        finally:
            f.close()
        if ok:
            util.log("keymap installed", xbmc.LOGINFO)
            xbmc.executebuiltin("Action(reloadkeymaps)")
        else:
            util.log("keymap install failed (profile not writable?)", xbmc.LOGWARNING)
    elif not want and current is not None:
        xbmcvfs.delete(_PATH)
        util.log("keymap removed", xbmc.LOGINFO)
        xbmc.executebuiltin("Action(reloadkeymaps)")
