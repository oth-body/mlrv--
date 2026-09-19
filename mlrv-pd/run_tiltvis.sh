#!/usr/bin/env bash
# Launches the mlrv-pd gyroscope visualizer (monome 64 + serialosc required).
# Run WITH the GUI to see the on-screen sliders (default); -nogui still
# drives the grid bubble-level headless.
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    "$@" \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    mlrv-pd/tiltvis_demo.pd
