#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1000, h=500)

# --- inlets: 4 audio (x ascending) + 1 control (rightmost) ---
IN = [p.obj(20 + 130 * v, 20, "inlet~") for v in range(4)]
CTRL_IN = p.obj(700, 20, "inlet")

HEADER = p.text(
    20, 460,
    "mixer.pd (Phase 3.2\\, mono): 4 inlet~ pre-fader voice audio (0..3) + 1 control "
    "inlet. control messages: \"vol <voice 0..3> <gain>\" \\, \"send <voice 0..3> <level>\" "
    "(both line~ 10 ramped\\, matching the original p vol_fade -- loadmess 1. then "
    "\\$1 10 into line~). outlet 0 = dry sum (voice*vol)\\, feeds master.pd. "
    "wet = voice*vol*send (post-fader tap\\, matching the original send-fader "
    "semantics)\\, summed and sent out send~ fxout -- master.pd receive~ fxin picks "
    "it up\\, one DSP block of latency across the abstraction boundary (gotcha 16). "
    "vols default to 1.0 at load\\; sends default to 0 (line~ own unset default -- "
    "no seeding needed). mute is vol <v> 0\\, no dedicated mute message. pan deferred "
    "(mono master)."
)

# --- per-voice vol and send multiply chains ---
VOL_LINE = [p.obj(20 + 130 * v, 60, "line~") for v in range(4)]
VOL_MULT = [p.obj(20 + 130 * v, 100, "*~") for v in range(4)]
SEND_LINE = [p.obj(20 + 130 * v, 140, "line~") for v in range(4)]
SEND_MULT = [p.obj(20 + 130 * v, 180, "*~") for v in range(4)]

for v in range(4):
    p.connect(IN[v], 0, VOL_MULT[v], 0)
    p.connect(VOL_LINE[v], 0, VOL_MULT[v], 1)
    p.connect(VOL_MULT[v], 0, SEND_MULT[v], 0)
    p.connect(SEND_LINE[v], 0, SEND_MULT[v], 1)

# --- dry sum: vol_mult[0..3] -> 3x +~ chain -> outlet~ ---
DRY_ADD1 = p.obj(20, 260, "+~")
DRY_ADD2 = p.obj(20, 300, "+~")
DRY_ADD3 = p.obj(20, 340, "+~")
DRY_OUT = p.obj(20, 400, "outlet~")

p.connect(VOL_MULT[0], 0, DRY_ADD1, 0)
p.connect(VOL_MULT[1], 0, DRY_ADD1, 1)
p.connect(DRY_ADD1, 0, DRY_ADD2, 0)
p.connect(VOL_MULT[2], 0, DRY_ADD2, 1)
p.connect(DRY_ADD2, 0, DRY_ADD3, 0)
p.connect(VOL_MULT[3], 0, DRY_ADD3, 1)
p.connect(DRY_ADD3, 0, DRY_OUT, 0)

# --- wet sum: send_mult[0..3] -> 3x +~ chain -> send~ fxout ---
WET_ADD1 = p.obj(280, 260, "+~")
WET_ADD2 = p.obj(280, 300, "+~")
WET_ADD3 = p.obj(280, 340, "+~")
WET_SEND = p.obj(280, 400, "send~ fxout")

p.connect(SEND_MULT[0], 0, WET_ADD1, 0)
p.connect(SEND_MULT[1], 0, WET_ADD1, 1)
p.connect(WET_ADD1, 0, WET_ADD2, 0)
p.connect(SEND_MULT[2], 0, WET_ADD2, 1)
p.connect(WET_ADD2, 0, WET_ADD3, 0)
p.connect(SEND_MULT[3], 0, WET_ADD3, 1)
p.connect(WET_ADD3, 0, WET_SEND, 0)

# --- control dispatch ---
ROUTE_VS = p.obj(700, 60, "route vol send")
ROUTE_VOL_V = p.obj(620, 100, "route 0 1 2 3")
ROUTE_SEND_V = p.obj(820, 100, "route 0 1 2 3")

p.connect(CTRL_IN, 0, ROUTE_VS, 0)
p.connect(ROUTE_VS, 0, ROUTE_VOL_V, 0)
p.connect(ROUTE_VS, 1, ROUTE_SEND_V, 0)

VOL_MSG = [p.msg(620 + 45 * v, 140, "\\$1 10") for v in range(4)]
SEND_MSG = [p.msg(820 + 45 * v, 140, "\\$1 10") for v in range(4)]

for v in range(4):
    p.connect(ROUTE_VOL_V, v, VOL_MSG[v], 0)
    p.connect(VOL_MSG[v], 0, VOL_LINE[v], 0)
    p.connect(ROUTE_SEND_V, v, SEND_MSG[v], 0)
    p.connect(SEND_MSG[v], 0, SEND_LINE[v], 0)

# --- default vol seeding: 1.0 at load, matching p vol_fade's loadmess 1. ---
SEED_LB = p.obj(950, 20, "loadbang")
SEED_T = p.obj(950, 60, "t b b b b")
SEED_MSG = [p.obj(920 + 20 * v, 100, "1 10") for v in range(4)]

p.connect(SEED_LB, 0, SEED_T, 0)
for v in range(4):
    p.connect(SEED_T, v, SEED_MSG[v], 0)
    p.connect(SEED_MSG[v], 0, VOL_LINE[v], 0)

p.write("../../abstractions/mixer.pd")
print("wrote mixer.pd:", len(p.objs), "objects,", len(p.conns), "connections")
