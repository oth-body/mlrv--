#!/usr/bin/env bash
# Launch mlrv-pd WITH its literal mapping GUI (1:1 mlrv recreation item 5).
# Unlike run_mlrv.sh, this intentionally runs WITH the Tk GUI (no -nogui):
# mlrv-gui.pd's sliders/toggles/buttons only move with a display. Pd flags
# must come BEFORE the patch filename (gotcha #22).
#
# Usage: mlrv-pd/run_mlrv_gui.sh
# Grid is optional: without serialosc running, the GUI widgets + MIDI/OSC
# mapping still drive the engine; grid keys/LEDs simply stay quiet.
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    -path mlrv-pd/samples \
    mlrv-pd/mlrv-gui.pd
