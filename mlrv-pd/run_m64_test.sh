#!/usr/bin/env bash
# Launches the monome greyscale 64 test patch. Pure control, no audio,
# no dac~. Same -path discipline as run_mlrv.sh and run_pong.sh:
# "$@" must come BEFORE the patch file (gotcha #22 -- Pd silently
# ignores flags placed after the file argument).
#
# Hardware: a real monome 64 + the serialosc daemon running, OR
# tests/fake_serialosc.py started in another terminal for headless
# validation of the discovery / handshake / key round-trip.
#
# Usage: mlrv-pd/run_m64_test.sh          (normal, console visible)
#         mlrv-pd/run_m64_test.sh -nogui   (headless; logs to stdout)
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    "$@" \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    mlrv-pd/m64_test.pd
