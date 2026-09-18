#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1400, h=700)

N = 4410

# --- source + capture arrays ---
SRC = [p.obj(20 + 60 * i, 600, f"table mlrv-mix-v{i} {N}") for i in range(4)]
CAP_DRY1 = p.obj(300, 600, f"table cap_dry1 {N}")
CAP_WET = p.obj(300, 640, f"table cap_wet {N}")
CAP_DRY2 = p.obj(300, 680, f"table cap_dry2 {N}")

# --- immediate setup: dsp on + read all 4 fixtures ---
LB0 = p.obj(20, 20, "loadbang")
DSP_ON = p.msg(20, 60, "\\; pd dsp 1")
p.connect(LB0, 0, DSP_ON, 0)

READ = []
SF = []
for i in range(4):
    r = p.msg(150 + 90 * i, 60, f"read /tmp/mlrv_mix_v{i}.wav mlrv-mix-v{i}")
    sf = p.obj(150 + 90 * i, 100, "soundfiler")
    p.connect(LB0, 0, r, 0)
    p.connect(r, 0, sf, 0)
    READ.append(r)
    SF.append(sf)

# --- 4 play_loop~ voices, one per fixture ---
PLOOP = [p.obj(20 + 130 * i, 160, f"play_loop~ mlrv-mix-v{i}") for i in range(4)]

# --- mixer under test ---
MIXER = p.obj(20, 220, "mixer")
for i in range(4):
    p.connect(PLOOP[i], 0, MIXER, i)

# --- wet return: receive~ fxout ---
RECV_FXOUT = p.obj(300, 220, "receive~ fxout")

# --- capture taps ---
TW_DRY1 = p.obj(20, 280, "tabwrite~ cap_dry1")
TW_WET = p.obj(300, 280, "tabwrite~ cap_wet")
TW_DRY2 = p.obj(20, 320, "tabwrite~ cap_dry2")
p.connect(MIXER, 0, TW_DRY1, 0)
p.connect(MIXER, 0, TW_DRY2, 0)
p.connect(RECV_FXOUT, 0, TW_WET, 0)

# --- timeline ---
# t150: start all 4 voices, set initial vols (vol0 stays default 1.0)
# t450: dry capture 1 (vol=[1,.5,.25,.5], send=[0,0,0,0])
# t850: vol0->0.5, send0->0.3
# t900: wet capture (only v0 contributes: const*0.5*0.3)
# t1350: vol3->0.75
# t1400: dry capture 2 (vol=[.5,.5,.25,.75])
# t2000/2010/2020: write captures
# t2100: quit
events = [
    (150, "1 4410 0", PLOOP[0], 0),
    (150, "1 4410 0", PLOOP[1], 0),
    (150, "1 4410 0", PLOOP[2], 0),
    (150, "1 4410 0", PLOOP[3], 0),
    (150, "vol 1 0.5", MIXER, 4),
    (150, "vol 2 0.25", MIXER, 4),
    (150, "vol 3 0.5", MIXER, 4),
    (450, None, TW_DRY1, 0),
    (850, "vol 0 0.5", MIXER, 4),
    (850, "send 0 0.3", MIXER, 4),
    (900, None, TW_WET, 0),
    (1350, "vol 3 0.75", MIXER, 4),
    (1400, None, TW_DRY2, 0),
    (2000, "write /tmp/mlrv_mix_cap_dry1.wav cap_dry1", SF[0], 0),
    (2010, "write /tmp/mlrv_mix_cap_wet.wav cap_wet", SF[1], 0),
    (2020, "write /tmp/mlrv_mix_cap_dry2.wav cap_dry2", SF[2], 0),
    (2100, "\\; pd quit", PLOOP[0], 0),
]
p.timeline(20, 400, events)

p.write("../test_mixer.pd")
print("wrote test_mixer.pd:", len(p.objs), "objects,", len(p.conns), "connections")
