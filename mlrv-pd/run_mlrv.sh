#!/usr/bin/env bash
# Launches the mlrv-pd instrument, with Pd's normal console/GUI visible
# (so you can see connection status and any error messages) -- the
# instrument itself is entirely grid-controlled, no on-screen controls
# to interact with. Pass -nogui yourself for a true headless run.
#
# Needs explicit -path flags -- soundfiler's own file lookups did not
# pick up a [declare -path samples] added inside mlrv.pd itself (tried,
# confirmed not working, not chased further; the command-line -path
# flag below is confirmed working and is what the whole rest of this
# port's test suites already rely on). See CLAUDE.md and the handoff
# log (Turn 16) for what that means if you touch this.
#
# Usage: mlrv-pd/run_mlrv.sh          (normal run, console visible)
#        mlrv-pd/run_mlrv.sh -nogui   (headless)
#
# Turn 21+ fix: Pd silently ignores flags placed AFTER the patch file
# it's told to open -- `pd file.pd -nogui` does NOT suppress the GUI,
# only `pd -nogui file.pd` does (probe-verified, no error either way,
# this script's own "-nogui" usage note above never actually worked
# until this fix). "$@" must come before the file argument, not after.
set -u
cd "$(dirname "$0")/.." || exit 1

exec pd \
    "$@" \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    -path mlrv-pd/samples \
    mlrv-pd/mlrv.pd
