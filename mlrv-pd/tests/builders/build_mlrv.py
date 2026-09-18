#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

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
    "as a real unresolved question in the handoff log)."
)

SERIALOSC = p.obj(20, 200, "serialosc 8000 /monome")
GRID = p.obj(20, 260, "grid")
FILE_POLY = p.obj(300, 200, "file_poly")
MAPPING = p.obj(300, 320, "mapping")
MASTER = p.obj(600, 200, "master")
DAC = p.obj(600, 260, "dac~ 1 2")

# --- control/LED chain ---
p.connect(SERIALOSC, 1, MAPPING, 0)     # grid_key (x y state) -> mapping inlet0
p.connect(FILE_POLY, 1, MAPPING, 1)     # info (loaded.../voice...) -> mapping inlet1
p.connect(MAPPING, 0, FILE_POLY, 0)     # commands (play.../stopall) -> file_poly inlet0
p.connect(MAPPING, 1, GRID, 0)          # LED (x y level) -> grid inlet0
p.connect(GRID, 0, SERIALOSC, 1)        # grid outlet -> serialosc LED-control inlet1

# --- audio chain (mixer.pd not yet wired in -- see header) ---
p.connect(FILE_POLY, 0, MASTER, 0)      # file_poly audio outlet~ -> master inlet~0
p.connect(MASTER, 0, DAC, 0)
p.connect(MASTER, 0, DAC, 1)

# master.pd's internal [receive~ fxin] has no matching [send~] until mixer.pd
# (or an effect) is wired in -- silences the harmless but noisy "no matching
# send" load-time error with an explicit silent placeholder, not a real bus.
FXIN_STUB = p.obj(600, 320, "sig~ 0")
FXIN_SEND = p.obj(600, 360, "send~ fxin")
p.connect(FXIN_STUB, 0, FXIN_SEND, 0)

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
    "status 2026-09-18: loads clean under pd -nogui. Real end-to-end test "
    "(real grid + real daemon + real audible sound) not yet run this turn "
    "-- see handoff log for what was actually verified vs. just wired."
)

p.write("../../mlrv.pd")
print("wrote mlrv.pd:", len(p.objs), "objects,", len(p.conns), "connections")
