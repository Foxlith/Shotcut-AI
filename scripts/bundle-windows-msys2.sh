#!/bin/bash
# Makes a portable Shotcut AI folder from a build installed into $1 by CMake
# (-DWINDOWS_DEPLOY=OFF) in an MSYS2 UCRT64 shell. The folder mirrors the MSYS2
# prefix, which is the layout that MLT and Shotcut expect with NODEPLOY:
#
#   bin/shotcut.exe, melt.exe, ffmpeg.exe, ffprobe.exe, whisper-cli.exe and every DLL
#                   they need
#   bin/qt.conf     Qt plugins and QML modules in share/qt6
#   lib/mlt         MLT modules          lib/frei0r-1  frei0r plugins
#   share/mlt       MLT data             share/shotcut QML, filter sets, resources
set -euo pipefail

DIST=${1:?usage: bundle-windows-msys2.sh <install dir>}
PREFIX=${MINGW_PREFIX:-/ucrt64}
SOURCE_DIR=$(cd "$(dirname "$0")/.." && pwd)

test -f "$DIST/bin/shotcut.exe" || { echo "Missing $DIST/bin/shotcut.exe"; exit 1; }

echo "== Helper programs"
for exe in melt.exe ffmpeg.exe ffprobe.exe; do
    cp -v "$PREFIX/bin/$exe" "$DIST/bin/"
done

echo "== MLT modules and data, frei0r plugins"
mkdir -p "$DIST/lib" "$DIST/share"
cp -r "$PREFIX/lib/mlt" "$DIST/lib/"
cp -r "$PREFIX/share/mlt" "$DIST/share/"
if [ -d "$PREFIX/lib/frei0r-1" ]; then
    cp -r "$PREFIX/lib/frei0r-1" "$DIST/lib/"
fi

echo "== Qt plugins, QML modules and translations"
mkdir -p "$DIST/share/qt6"
cp -r "$PREFIX/share/qt6/plugins" "$DIST/share/qt6/"
cp -r "$PREFIX/share/qt6/qml" "$DIST/share/qt6/"
if [ -d "$PREFIX/share/qt6/translations" ]; then
    cp -r "$PREFIX/share/qt6/translations" "$DIST/share/qt6/"
fi
cat > "$DIST/bin/qt.conf" <<'EOF'
[Paths]
Prefix = ..
Binaries = bin
Libraries = bin
Plugins = share/qt6/plugins
QmlImports = share/qt6/qml
Translations = share/qt6/translations
EOF

echo "== Fontconfig configuration (text in MLT)"
if [ -d "$PREFIX/etc/fonts" ]; then
    mkdir -p "$DIST/etc"
    cp -r "$PREFIX/etc/fonts" "$DIST/etc/"
fi

echo "== Grafito theme next to the program"
cp -v "$SOURCE_DIR/capcut_theme.qss" "$DIST/bin/"

echo "== Speech to text (whisper.cpp)"
# Shotcut runs bin/whisper-cli.exe for Subtitles > Speech to Text, and so does the media
# analysis server. ggml loads its CPU and Vulkan backends at run time, so ldd does not see
# them; their own DLLs are found below.
if [ -f "$PREFIX/bin/whisper-cli.exe" ]; then
    cp -v "$PREFIX/bin/whisper-cli.exe" "$DIST/bin/"
    for dll in "$PREFIX"/bin/*ggml-cpu*.dll "$PREFIX"/bin/*ggml-vulkan*.dll; do
        if [ -e "$dll" ]; then cp -v "$dll" "$DIST/bin/"; fi
    done
fi

echo "== DLLs"
# ldd lists the whole dependency tree of each binary; keep the ones from the MSYS2
# prefix and repeat until nothing new is copied (the copied DLLs are scanned too).
while true; do
    before=$(ls "$DIST/bin" | wc -l)
    find "$DIST" -type f \( -iname '*.exe' -o -iname '*.dll' \) -print0 \
        | xargs -0 -n 50 ldd 2>/dev/null \
        | awk -v prefix="$PREFIX/bin/" 'index($3, prefix) == 1 { print $3 }' \
        | sort -u \
        | while read -r dll; do
            name=$(basename "$dll")
            [ -e "$DIST/bin/$name" ] || cp "$dll" "$DIST/bin/"
        done
    after=$(ls "$DIST/bin" | wc -l)
    [ "$before" -eq "$after" ] && break
done
echo "$(ls "$DIST/bin" | wc -l) files in bin"

echo "== Launcher"
cat > "$DIST/Shotcut AI.bat" <<'EOF'
@echo off
start "" "%~dp0bin\shotcut.exe" %*
EOF

du -sh "$DIST"
