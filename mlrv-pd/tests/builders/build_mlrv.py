#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
from mlrv_core import build_core

p = Patch(w=1200, h=700)

HEADER = p.text(
    20, 20,
    "mlrv.pd -- top-level instrument (Turn 16\\, 2026-09-18). Wires the 8 "
    "independently-verified components into one instrument: serialosc "
    "(grid I/O) -> mapping (key->action) -> file_poly (sample playback) "
    "-> master (output bus) -> dac~. grid.pd sits between mapping and "
    "serialosc\\'s LED inlet (protocol-agnostic passthrough\\, kept for "
    "the correct architectural seam even though it is currently a no-op). "
    "mixer.pd is NOT wired in yet -- file_poly still sums its own 4 "
    "voices internally and feeds master directly (documented TODO\\, "
    "CLAUDE.md). On load: enables DSP\\, sets master gain to 0.8 (headroom "
    "margin)\\, triggers a serialosc rescan\\, and loads two short "
    "placeholder demo tones (mlrv-pd/samples/) into slots 0 and 1 so "
    "pressing the two leftmost trigger-row keys (y=7) produces audible "
    "sound with zero manual setup -- not real musical content\\, just "
    "honest proof that the full signal path works. Load real samples "
    "with \"load <slot 0..7> <path>\" sent to the file_poly instance "
    "directly\\, or edit the loadbang section below. Launch via "
    "mlrv-pd/run_mlrv.sh\\, not pd directly on this file -- it needs "
    "-path flags (abstractions\\, patchers\\, samples) that [declare "
    "-path] could not be made to cover for soundfiler\\'s own file "
    "lookups (tried\\, did not work\\, not chased further -- documented "
    "as a real unresolved question in the handoff log). Core wiring "
    "shared with tests/test_mlrv.pd via mlrv_core.py -- see "
    "run_mlrv_test.sh for the automated (no listening required) "
    "regression suite."
)

core = build_core(p)
SERIALOSC, GRID, FILE_POLY, MAPPING, MASTER = (
    core["SERIALOSC"], core["GRID"], core["FILE_POLY"], core["MAPPING"], core["MASTER"]
)

DAC = p.obj(600, 260, "dac~ 1 2")
p.connect(FILE_POLY, 0, MASTER, 0)      # file_poly audio outlet~ -> master inlet~0
p.connect(MASTER, 0, DAC, 0)
p.connect(MASTER, 0, DAC, 1)

# --- bootstrap ---
LB = p.obj(20, 400, "loadbang")
DSP_ON = p.msg(20, 440, "\\; pd dsp 1")
GAIN = p.msg(150, 440, "0.8")
RESCAN = p.msg(280, 440, "bang")
LOAD0 = p.msg(410, 440, "load 0 demo-tone-0.wav")
LOAD1 = p.msg(410, 480, "load 1 demo-tone-1.wav")

p.connect(LB, 0, DSP_ON, 0)
p.connect(LB, 0, GAIN, 0)
p.connect(GAIN, 0, MASTER, 1)
p.connect(LB, 0, RESCAN, 0)
p.connect(RESCAN, 0, SERIALOSC, 0)
p.connect(LB, 0, LOAD0, 0)
p.connect(LOAD0, 0, FILE_POLY, 0)
p.connect(LB, 0, LOAD1, 0)
p.connect(LOAD1, 0, FILE_POLY, 0)

FOOTER = p.text(
    20, 520,
    "status 2026-09-18 (turn 16): loads clean under pd -nogui \\; a "
    "simulated grid key press (fake_serialosc.py) produced real "
    "correctly-scaled audio through the whole chain (handoff log). "
    "turn 17: real-hardware live listening test deferred by request -- "
    "run_mlrv_test.sh (automated\\, fake daemon\\, no listening needed) "
    "is the regression suite to trust instead."
)

p.write("../../mlrv.pd")
print("wrote mlrv.pd:", len(p.objs), "objects,", len(p.conns), "connections")
