#!/usr/bin/env bash
# Builds mlrv-x86_64.AppImage: a self-contained, double-clickable package
# of the mlrv-pd instrument -- bundles Pd itself (binary + its "extra"
# objects/support files) and this port's abstractions/patchers/samples,
# so end users don't need Pd installed separately. Linux x86_64 only.
#
# Requires network access (downloads linuxdeploy + an AppImage runtime
# on first run; both are cached in this directory, gitignored, not
# committed). Needs a system Pd install to bundle from (tested against
# 0.56.5); FUSE is used to run/test the resulting AppImage but is not
# required to just build one.
#
# Usage: mlrv-pd/package/build_appimage.sh
set -eu
cd "$(dirname "$0")"

PD_BIN="$(command -v pd)"
if [ -z "$PD_BIN" ]; then
    echo "FAIL: no 'pd' found on PATH -- install Pd first (this script bundles a local install, it does not build Pd from source)" >&2
    exit 1
fi
PD_LIBDIR="$(dirname "$(dirname "$PD_BIN")")/lib/pd"
if [ ! -d "$PD_LIBDIR" ]; then
    echo "FAIL: expected Pd support files at $PD_LIBDIR, not found" >&2
    exit 1
fi

if [ ! -x ./linuxdeploy ]; then
    echo "Downloading linuxdeploy..."
    curl -sL -A "Mozilla/5.0" -o linuxdeploy \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x linuxdeploy
fi

rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/lib/pd AppDir/usr/share/mlrv/pd
cp "$PD_BIN" AppDir/usr/bin/pd
cp -r "$PD_LIBDIR"/* AppDir/usr/lib/pd/
cp -r ../abstractions ../patchers AppDir/usr/share/mlrv/pd/
[ -d ../samples ] && cp -r ../samples AppDir/usr/share/mlrv/pd/
cp ../mlrv.pd AppDir/usr/share/mlrv/pd/

# AppRun, mlrv.desktop, mlrv.png are checked into this directory (not
# generated) -- copy them into the AppDir being assembled.
cp AppRun.src AppDir/AppRun
chmod +x AppDir/AppRun
cp mlrv.desktop.src AppDir/mlrv.desktop
cp mlrv.png.src AppDir/mlrv.png

rm -f mlrv-x86_64.AppImage
./linuxdeploy --appdir AppDir --executable AppDir/usr/bin/pd \
    --desktop-file AppDir/mlrv.desktop --icon-file AppDir/mlrv.png \
    --output appimage

echo "built: $(pwd)/mlrv-x86_64.AppImage"
