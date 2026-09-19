#!/usr/bin/env bash
# Launches the mlrv-pd glow toy (monome 64 grid + serialosc daemon required).
# Same -path discipline as run_mlrv.sh: "$@" must come BEFORE the patch file.
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    "$@" \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    mlrv-pd/glow_demo.pd
