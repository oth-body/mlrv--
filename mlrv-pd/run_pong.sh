#!/usr/bin/env bash
# Launches the mlrv-pd pong demo (monome 64 grid + serialosc daemon required).
# Same -path discipline as run_mlrv.sh: "$@" must come BEFORE the patch file.
#
# Usage: mlrv-pd/run_pong.sh          (normal run, console visible)
#        mlrv-pd/run_pong.sh -nogui   (headless; logs to stdout)
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    "$@" \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    mlrv-pd/pong_demo.pd
