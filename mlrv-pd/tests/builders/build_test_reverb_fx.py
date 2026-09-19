#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_reverb_fx.pd -- verifies reverb_fx~.pd
against real captured audio, not just a clean load.

Unlike delay_fx~.pd (discrete, countable echoes), a real FDN reverb's
impulse response is dense, noise-like, and non-repeating -- so this test
checks windowed ENERGY DECAY over time, not discrete peak regions:
  1. burst1, liveness=90 (long): capture a 1.5s window, split into 100ms
     chunks, and confirm energy decays over time (later chunks quieter
     than earlier ones) while still being clearly non-silent well past
     where the dry burst itself (2.3ms) would have ended -- proof this
     is a real decaying reverb tail, not just a burst passthrough.
  2. burst2, liveness=10 (short), fired well after burst1's tail has
     decayed: confirms the SAME 500ms-later chunk has dramatically less
     energy than the liveness=90 case did at the same offset -- proof
     the liveness parameter genuinely controls decay time, not just a
     fixed characteristic of rev3~ itself.

Run from builders/: python3 build_test_reverb_fx.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=500)

BURST_N = 100  # ~2.3ms at 44100Hz

SRC = p.obj(20, 20, f"table mlrv-rfx-src {BURST_N}")
CAP1 = p.obj(200, 20, "table mlrv-rfx-cap1 66150")   # 1.5s @ 44100Hz
CAP2 = p.obj(400, 20, "table mlrv-rfx-cap2 30870")   # 700ms

lb = p.obj(20, 60, "loadbang")
dsp_on = p.msg(20, 90, "\\; pd dsp 1")
p.connect(lb, 0, dsp_on, 0)
read_msg = p.msg(150, 90, "read /tmp/mlrv_rfx_burst.wav mlrv-rfx-src")
sf_read = p.obj(150, 130, "soundfiler")
p.connect(lb, 0, read_msg, 0)
p.connect(read_msg, 0, sf_read, 0)

tabplay = p.obj(20, 170, "tabplay~ mlrv-rfx-src")
send_fxout = p.obj(20, 210, "send~ fxout")
p.connect(tabplay, 0, send_fxout, 0)

rfx = p.obj(300, 170, "reverb_fx~")

tw1 = p.obj(300, 250, "tabwrite~ mlrv-rfx-cap1")
tw2 = p.obj(300, 290, "tabwrite~ mlrv-rfx-cap2")
p.connect(rfx, 0, tw1, 0)
p.connect(rfx, 0, tw2, 0)

sf_write1 = p.obj(600, 250, "soundfiler")
sf_write2 = p.obj(600, 290, "soundfiler")

events = [
    (50,  "liveness 90", rfx, 0),
    (50,  "level 90", rfx, 0),
    (50,  "crossover 3000", rfx, 0),
    (50,  "damping 20", rfx, 0),
    (100, "bang", tabplay, 0),
    (100, None, tw1, 0),
    (2000, "liveness 10", rfx, 0),
    (2000, "bang", tabplay, 0),
    (2000, None, tw2, 0),
    (3700, "write /tmp/mlrv_rfx_cap1.wav mlrv-rfx-cap1", sf_write1, 0),
    (3720, "write /tmp/mlrv_rfx_cap2.wav mlrv-rfx-cap2", sf_write2, 0),
    (3800, "\\; pd quit", sf_write2, 0),
]
p.timeline(20, 350, events)

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/osc-control/mlrv-pd/tests/test_reverb_fx.pd")
print("wrote test_reverb_fx.pd:", len(p.objs), "objects,", len(p.conns), "connections")
