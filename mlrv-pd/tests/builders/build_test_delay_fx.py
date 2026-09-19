#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_delay_fx.pd -- verifies delay_fx~.pd
against real captured audio, not just a clean load.

Drives delay_fx~.pd exactly like mixer.pd/master.pd would in the real
instrument: a `[send~ fxout]` (standing in for mixer's per-voice wet sum)
feeds it, and its real `[outlet~]` is tapped directly (no `[receive~
fxin]` needed here -- that bus only exists once in the real instrument,
summed from every effect's outlet~ by the parent patch; this test only
has one effect, so a direct outlet~ tap is simpler and just as valid).

Two scenarios in one timeline (one Pd process, not two, since burst1's
feedback=0 tail is fully silent well before burst2 fires 600ms later):
  1. time=200ms, feedback=0: burst1 fires, capture1 should show exactly
     one delayed copy of the burst and silence everywhere else (no
     repeats -- proves feedback=0 is truly off, not just quiet).
  2. time=200ms, feedback=0.5: burst2 fires 600ms later (comfortably
     after burst1's single echo has fully decayed), capture2 should show
     TWO copies 200ms apart (the direct echo, then one feedback repeat at
     roughly half the peak amplitude, minus whatever a real [hip~ 5]
     DC-blocker and the two send~/receive~ block-latency hops (gotcha 16,
     crossed twice here: test->delay_fx~ and delay_fx~->test) cost).

Run from builders/: python3 build_test_delay_fx.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=500)

BURST_N = 100  # ~2.3ms at 44100Hz -- short enough to read as a clean spike, not a sustained tone

SRC = p.obj(20, 20, f"table mlrv-dfx-src {BURST_N}")
CAP1 = p.obj(200, 20, "table mlrv-dfx-cap1 22050")   # 500ms
CAP2 = p.obj(400, 20, "table mlrv-dfx-cap2 30870")   # 700ms

lb = p.obj(20, 60, "loadbang")
dsp_on = p.msg(20, 90, "\\; pd dsp 1")
p.connect(lb, 0, dsp_on, 0)
read_msg = p.msg(150, 90, "read /tmp/mlrv_dfx_burst.wav mlrv-dfx-src")
sf_read = p.obj(150, 130, "soundfiler")
p.connect(lb, 0, read_msg, 0)
p.connect(read_msg, 0, sf_read, 0)

tabplay = p.obj(20, 170, "tabplay~ mlrv-dfx-src")
send_fxout = p.obj(20, 210, "send~ fxout")
p.connect(tabplay, 0, send_fxout, 0)

dfx = p.obj(300, 170, "delay_fx~")

tw1 = p.obj(300, 250, "tabwrite~ mlrv-dfx-cap1")
tw2 = p.obj(300, 290, "tabwrite~ mlrv-dfx-cap2")
p.connect(dfx, 0, tw1, 0)
p.connect(dfx, 0, tw2, 0)

sf_write1 = p.obj(600, 250, "soundfiler")
sf_write2 = p.obj(600, 290, "soundfiler")

events = [
    (50,  "time 200", dfx, 0),
    (50,  "feedback 0", dfx, 0),
    (100, "bang", tabplay, 0),
    (100, None, tw1, 0),                 # arm capture1 same tick as burst1
    (700, "feedback 0.5", dfx, 0),
    (700, "bang", tabplay, 0),
    (700, None, tw2, 0),                 # arm capture2 same tick as burst2
    (1450, "write /tmp/mlrv_dfx_cap1.wav mlrv-dfx-cap1", sf_write1, 0),
    (1460, "write /tmp/mlrv_dfx_cap2.wav mlrv-dfx-cap2", sf_write2, 0),
    (1550, "\\; pd quit", sf_write2, 0),
]
p.timeline(20, 350, events)

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/osc-control/mlrv-pd/tests/test_delay_fx.pd")
print("wrote test_delay_fx.pd:", len(p.objs), "objects,", len(p.conns), "connections")
