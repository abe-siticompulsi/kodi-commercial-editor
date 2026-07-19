#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Verify the addon and package it as an installable Kodi zip in dist/.
# Usage: scripts/package.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ADDON_ID="service.commercial-editor"
VERSION=$(python3 -c "import xml.dom.minidom; \
    print(xml.dom.minidom.parse('addon.xml').documentElement.getAttribute('version'))")

echo "== verify =="
python3 - <<'EOF'
import glob, re, py_compile, xml.dom.minidom

for f in ['default.py', 'service.py'] + glob.glob('resources/lib/*.py'):
    py_compile.compile(f, doraise=True)
print('python: OK')

for f in ['addon.xml', 'resources/settings.xml'] + glob.glob('resources/skins/Default/1080i/*.xml'):
    xml.dom.minidom.parse(f)
keymap_src = open('resources/lib/keymap.py').read()
xml.dom.minidom.parseString(re.search(r'_CONTENT = """(.*?)"""', keymap_src, re.S).group(1))
print('xml: OK')

src = ''.join(open(f).read() for f in glob.glob('resources/lib/*.py') + ['default.py', 'service.py'])
used = set(re.findall(r'L\((\d+)\)', src))
en = open('resources/language/resource.language.en_gb/strings.po').read()
en_ids = set(re.findall(r'#(\d+)', en))
missing = used - en_ids
assert not missing, f'strings used in code but missing from en_gb: {missing}'
for po in glob.glob('resources/language/resource.language.*/strings.po'):
    lang = po.split('.')[-2].split('/')[0]
    ids = set(re.findall(r'#(\d+)', open(po).read()))
    assert ids == en_ids, f'{lang}: id mismatch vs en_gb: {ids ^ en_ids}'
print(f'strings: OK ({len(en_ids)} ids, {len(glob.glob("resources/language/resource.language.*"))} languages)')
EOF

echo "== package =="
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
rsync -a \
    --exclude '.git' \
    --exclude '.claude' \
    --exclude '.gitignore' \
    --exclude '.DS_Store' \
    --exclude 'LOCAL-FINDINGS.md' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.zip' \
    --exclude 'dist' \
    --exclude 'scripts' \
    ./ "$STAGE/$ADDON_ID/"
mkdir -p dist
ZIP="dist/${ADDON_ID}-${VERSION}.zip"
rm -f "$ZIP"
(cd "$STAGE" && zip -rq "$OLDPWD/$ZIP" "$ADDON_ID")
SIZE=$(wc -c < "$ZIP" | tr -d ' ')
if command -v md5sum >/dev/null; then SUM=$(md5sum "$ZIP" | cut -d' ' -f1); else SUM=$(md5 -q "$ZIP"); fi
echo "built: $ZIP"
echo "size:  $SIZE bytes"
echo "md5:   $SUM"
echo "After copying to the box, verify BOTH match before installing"
echo "(a partial copy poisons Kodi's per-path zip cache until restart)."
