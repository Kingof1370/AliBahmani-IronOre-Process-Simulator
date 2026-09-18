#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Cross-build of the Windows (x64) installer + portable package for
#   AliBahmani IronOre Process Simulator v1.0.0
#   Developer / Manufacturer: Ali Bahmani (علی بهمنی) - Contact: 09915420558
#
# Runs on Linux/macOS. Assembles a real Windows package by combining
#   * the official Windows *embeddable* CPython distribution (python.org),
#   * win_amd64 / cp311 binary wheels from PyPI (full transitive closure),
#   * the application sources, documentation and sample engineering outputs,
# and packaging it with NSIS (makensis), which is a genuine Windows installer
# compiler that also cross-compiles from Linux. No PyInstaller, no Windows SDK.
#
# Usage:  bash installer/cross_build/build_windows_installer.sh
# ---------------------------------------------------------------------------
set -euo pipefail

PYVER="3.11.9"
PYTAG="311"
PKGS="openpyxl ezdxf reportlab pillow numpy imageio imageio-ffmpeg PySide6-Essentials shiboken6"

CROSS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$CROSS/../.." && pwd)"
BUILD="${AH_SIM_BUILD_DIR:-/tmp/ahsim_cross_build}"
SETUP_OUT="$REPO/installer/SETUP_OUTPUT"
PAYLOAD="$BUILD/payload"

echo "repo  : $REPO"
echo "build : $BUILD"

rm -rf "$BUILD"
mkdir -p "$BUILD/wheels" "$PAYLOAD/runtime" "$PAYLOAD/app" "$PAYLOAD/bin" "$SETUP_OUT"

echo "== 1/8  Windows embeddable CPython $PYVER (amd64) =="
curl -fsSL -o "$BUILD/python-embed.zip" \
  "https://www.python.org/ftp/python/${PYVER}/python-${PYVER}-embed-amd64.zip"
unzip -q -o "$BUILD/python-embed.zip" -d "$PAYLOAD/runtime/python"
test -f "$PAYLOAD/runtime/python/python.exe"

echo "== 2/8  resolving + downloading win_amd64 / cp${PYTAG} wheels =="
python3 -m pip download --quiet --only-binary=:all: \
  --platform win_amd64 --python-version "$PYTAG" --implementation cp \
  --dest "$BUILD/wheels" $PKGS
ls -1 "$BUILD/wheels" | sed 's/^/    /'

echo "== 3/8  enabling site-packages inside the embeddable runtime =="
printf 'python%s.zip\r\n.\r\nLib\\site-packages\r\nimport site\r\n' "$PYTAG" \
  > "$PAYLOAD/runtime/python/python${PYTAG}._pth"
SITE="$PAYLOAD/runtime/python/Lib/site-packages"
mkdir -p "$SITE"
for w in "$BUILD"/wheels/*.whl; do unzip -q -o "$w" -d "$SITE"; done

echo "== 4/8  application sources, docs, sample outputs =="
cp -r "$REPO/ahsim"        "$PAYLOAD/app/"
cp    "$REPO/ahsim_app.py" "$PAYLOAD/app/"
cp -r "$REPO/docs"         "$PAYLOAD/app/"
cp -r "$REPO/tests"        "$PAYLOAD/app/"
cp -r "$REPO/scripts"      "$PAYLOAD/app/"
mkdir -p "$PAYLOAD/app/installer"
tar -C "$REPO/installer" --exclude=SETUP_OUTPUT --exclude=_build --exclude=__pycache__ -cf - . \
  | tar -C "$PAYLOAD/app/installer" -xf -
mkdir -p "$PAYLOAD/app/RELEASE"
cp -r "$REPO/RELEASE/."    "$PAYLOAD/app/RELEASE/"
cp "$REPO/README.md" "$REPO/LICENSE" "$PAYLOAD/app/" 2>/dev/null || true
cp    "$CROSS/selfcheck.py"         "$PAYLOAD/bin/"
cp    "$CROSS/Run_AH-SIM.cmd"       "$PAYLOAD/app/"
cp    "$CROSS/Generate_Reports.cmd" "$PAYLOAD/app/"
find "$PAYLOAD" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "== 5/8  dependency resolution report (win_amd64) =="
python3 -m pip install --dry-run --quiet \
  --platform win_amd64 --python-version "$PYTAG" --implementation cp \
  --only-binary=:all: --target "$BUILD/_resolve" --report "$BUILD/report.json" $PKGS
python3 - "$BUILD/report.json" <<'PYEOF'
import json, sys
rep = json.load(open(sys.argv[1]))
names = sorted(f"{i['metadata']['name']}=={i['metadata']['version']}" for i in rep["install"])
print(f"    resolved closure: {len(names)} distributions")
for n in names:
    print("      -", n)
PYEOF

echo "== 6/8  compiling the NSIS installer =="
NSI="$REPO/installer/AH-SIM_SelfContained_Setup.nsi"
if [ -f "/usr/share/nsis/Contrib/Language files/Farsi.nsh" ]; then
  echo "    Farsi language file found - bilingual installer"
else
  echo "    Farsi language file missing - compiling English only"
  sed 's/^!insertmacro MUI_LANGUAGE "Farsi"$//' "$NSI" > "$BUILD/nsi_en_only.nsi"
  NSI="$BUILD/nsi_en_only.nsi"
fi
makensis -V2 -DPAYLOAD="$PAYLOAD" -DOUTDIR="$SETUP_OUT" "$NSI"

echo "== 7/8  portable (no-install) package =="
PORT="$REPO/installer/SETUP_OUTPUT/AliBahmani_IronOre_Process_Simulator_v1.0.0_portable_win64"
rm -rf "$PORT"
mkdir -p "$PORT"
cp -r "$PAYLOAD/app"     "$PORT/app"
cp -r "$PAYLOAD/runtime" "$PORT/runtime"
cp -r "$PAYLOAD/bin"     "$PORT/bin"
cp "$CROSS/Portable_README.txt" "$PORT/README_FIRST.txt"
( cd "$(dirname "$PORT")" && zip -q -r -9 "$(basename "$PORT").zip" "$(basename "$PORT")" )
rm -rf "$PORT"

echo "== 8/8  result =="
ls -l "$SETUP_OUT"
sha256sum "$SETUP_OUT"/*.exe "$SETUP_OUT"/*.zip
