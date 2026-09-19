#!/usr/bin/env python3
"""Builder for mlrv-pd/patchers/tiltvis.pd -- gyroscope visualizer for the
monome 64 (greyscale/varibright).

  serialosc.pd outlet 1 (keys) -> tiltvis inlet 0
  serialosc.pd outlet 2 (tilt "sensor x y z") -> tiltvis inlet 1
  tiltvis outlet 0 (LED "x y level") -> grid.pd -> serialosc.pd LED inlet

Display: center cross (level 2), bubble at tilt deviation (level 15),
right column = z bar (level 8). Any key press recenters the level and
prints the center. Direct messages: center, tilt <x> <y> <z>.
Event-driven (no metro). [change] gates all LED traffic to real moves.

Run from this directory:  python3 build_tiltvis.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1400, h=900)

p.text(20, 20,
    "tiltvis.pd: gyroscope visualizer for a greyscale/varibright 64 \\, on mlrv-pd's "
    "serialosc.pd + grid.pd primitives. inlet 0: grid keys (list x y state -- any press "
    "recenters) + direct center / tilt <x> <y> <z>. inlet 1: tilt sensor tuples "
    "(sensor x y z). outlet 0 = LED x y level: cross level 2 \\, bubble 15 \\, "
    "right column = tilt-ENERGY bar level 8. outlet 1 = tilt <x> <y> <energy255> per "
    "event (drives the on-screen sliders) + center <x> <y> <z> on recalibrate. "
    "NOTE: this grid's sensor is 2-axis -- its z field reads a constant 0 "
    "(probe-verified across thousands of live events) \\, so the energy channel is "
    "sqrt(dx^2+dy^2) of tilt deviation instead (bar int(m*0.1) \\, slider min(m*2.5\\,255)). "
    "bubble = int(4.0+dev*0.07) clamped 0..7 (full deflection at +-50). "
    "[change] on px/py/h means silent grid = silent wire. "
    "verified: tests/run_tiltvis_test.sh.")

IN0 = p.obj(20, 160, "inlet")
IN1 = p.obj(200, 160, "inlet")
OUT_LED = p.obj(20, 840, "outlet")
OUT_INFO = p.obj(200, 840, "outlet")

TXH = p.obj(300, 200, "float 127")
TXH2 = p.obj(330, 200, "float 127")
TYH = p.obj(360, 200, "float 127")
TZH = p.obj(420, 200, "float 127")
PXST = p.obj(480, 200, "float 4")
PYST = p.obj(540, 200, "float 4")
PBXST = p.obj(600, 200, "float 4")
PBYST = p.obj(660, 200, "float 4")
HST = p.obj(720, 200, "float 0")

DEVX = p.obj(300, 260, "expr \\$f1-\\$f2")
DEVY = p.obj(420, 260, "expr \\$f1-\\$f2")
DXH = p.obj(360, 260, "float 0")
DYH = p.obj(480, 260, "float 0")
DXC = p.obj(300, 290, "t f f f")
TB_DY = p.obj(360, 290, "t b")
DYC = p.obj(420, 290, "t f f")
MAGEXPR = p.obj(540, 290, "expr sqrt(\\$f1*\\$f1+\\$f2*\\$f2)")
MSC = p.obj(620, 290, "expr \\$f1*2.5")
MIN255 = p.obj(620, 330, "min 255")
INF_T = p.obj(620, 370, "t f f f")
TB_TY = p.obj(560, 370, "t b")
TB_TX = p.obj(680, 370, "t b")
PKI = p.obj(620, 410, "pack f f f")
MSI = p.msg(620, 450, "tilt \\$1 \\$2 \\$3")
HEXPR = p.obj(540, 260, "expr int(\\$f1*0.1)")
MIN7 = p.obj(540, 300, "min 7")
p.connect(DEVX, 0, DXC, 0)
p.connect(DXC, 1, DXH, 1)
p.connect(DXC, 1, MAGEXPR, 1)
p.connect(DXC, 0, TB_DY, 0)
p.connect(TB_DY, 0, DYH, 0)
p.connect(DYH, 0, MAGEXPR, 0)
p.connect(MAGEXPR, 0, MSC, 0)
p.connect(MSC, 0, MIN255, 0)
p.connect(MIN255, 0, INF_T, 0)
p.connect(INF_T, 2, TB_TY, 0)
p.connect(TB_TY, 0, TYH, 0)
p.connect(TYH, 0, PKI, 1)
p.connect(INF_T, 1, PKI, 2)
p.connect(INF_T, 0, TB_TX, 0)
p.connect(TB_TX, 0, TXH2, 0)
p.connect(TXH2, 0, PKI, 0)
p.connect(PKI, 0, MSI, 0)
p.connect(MSI, 0, OUT_INFO, 0)
p.connect(MAGEXPR, 0, HEXPR, 0)
p.connect(HEXPR, 0, MIN7, 0)
p.connect(DEVY, 0, DYC, 0)
p.connect(DYC, 1, DYH, 1)
PXEXPR = p.obj(300, 320, "expr int(4.0+\\$f1*0.07)")
PYEXPR = p.obj(420, 320, "expr int(4.0+\\$f1*0.07)")
CLX0 = p.obj(300, 380, "max 0")
CLX7 = p.obj(300, 420, "min 7")
CLY0 = p.obj(420, 380, "max 0")
CLY7 = p.obj(420, 420, "min 7")
CHX = p.obj(300, 460, "change")
CHY = p.obj(420, 460, "change")
CHH = p.obj(540, 460, "change")
p.connect(DXC, 2, PXEXPR, 0)
p.connect(PXEXPR, 0, CLX0, 0)
p.connect(CLX0, 0, CLX7, 0)
p.connect(CLX7, 0, CHX, 0)
p.connect(DYC, 0, PYEXPR, 0)
p.connect(PYEXPR, 0, CLY0, 0)
p.connect(CLY0, 0, CLY7, 0)
p.connect(CLY7, 0, CHY, 0)
p.connect(MIN7, 0, CHH, 0)

# store-first fan-out order matters: the value store is connected before the
# render trigger, so the render always reads the fresh value.
RND = p.obj(20, 560, "t b b b")
ET = p.obj(20, 610, "t b b")
PKE = p.obj(20, 660, "pack f f 0")
CT = p.obj(200, 610, "t b b b b")
CM = [p.msg(200 + i * 60, 660, m) for i, m in
      enumerate(["3 3 2", "4 3 2", "3 4 2", "4 4 2"])]
DT = p.obj(560, 610, "t b b")
PKD = p.obj(560, 660, "pack f f 15")
p.connect(CHX, 0, PXST, 1)
p.connect(CHX, 0, RND, 0)
p.connect(CHY, 0, PYST, 1)
p.connect(CHY, 0, RND, 0)
p.connect(RND, 2, ET, 0)
p.connect(ET, 1, PBYST, 0)
p.connect(PBYST, 0, PKE, 1)
p.connect(ET, 0, PBXST, 0)
p.connect(PBXST, 0, PKE, 0)
p.connect(PKE, 0, OUT_LED, 0)
p.connect(RND, 1, CT, 0)
for i, m in enumerate(CM):
    p.connect(CT, i, m, 0)
    p.connect(m, 0, OUT_LED, 0)
p.connect(RND, 0, DT, 0)
p.connect(DT, 1, PYST, 0)
p.connect(PYST, 0, PKD, 1)
p.connect(PYST, 0, PBYST, 1)
p.connect(DT, 0, PXST, 0)
p.connect(PXST, 0, PKD, 0)
p.connect(PXST, 0, PBXST, 1)
p.connect(PKD, 0, OUT_LED, 0)

# z-bar: h fans to 8 row gates; row r lights iff r >= 7-h.
H_T = p.obj(760, 560, "t f f f f f f f f")
for r in range(8):
    RX = p.obj(760 + r * 60, 610, "expr \\$f1>=%d" % (7 - r))
    M8 = p.obj(760 + r * 60, 660, "* 8")
    RM = p.msg(760 + r * 60, 710, "7 %d \\$1" % r)
    p.connect(H_T, r, RX, 0)
    p.connect(RX, 0, M8, 0)
    p.connect(M8, 0, RM, 0)
    p.connect(RM, 0, OUT_LED, 0)
p.connect(CHH, 0, HST, 1)
p.connect(CHH, 0, H_T, 0)

# tilt distribution triggers (shared by serial + direct paths via fan-in)
ZT = p.obj(300, 740, "t f f")
YT = p.obj(420, 740, "t f f")
XT = p.obj(540, 740, "t f f")
p.connect(ZT, 1, TZH, 1)
p.connect(YT, 1, TYH, 1)
p.connect(YT, 0, DEVY, 0)
p.connect(XT, 1, TXH, 1)
p.connect(XT, 1, TXH2, 1)
p.connect(XT, 0, DEVX, 0)

# ---------------- tilt sources ----------------
RIN1 = p.obj(200, 1060, "route list")
UNP_S = p.obj(200, 1020, "unpack f f f f")
UNP_S2 = p.obj(320, 1020, "unpack f f f f")
p.connect(IN1, 0, RIN1, 0)
p.connect(RIN1, 0, UNP_S, 0)
p.connect(RIN1, 1, UNP_S2, 0)
p.connect(UNP_S, 2, ZT, 0)
p.connect(UNP_S2, 2, ZT, 0)
p.connect(UNP_S, 1, YT, 0)
p.connect(UNP_S2, 1, YT, 0)
p.connect(UNP_S, 0, XT, 0)
p.connect(UNP_S2, 0, XT, 0)

# ---------------- keys + direct tilt/center ----------------
RIN0 = p.obj(20, 1060, "route list center tilt")
UNP = p.obj(20, 1020, "unpack f f f")
PK = p.obj(20, 980, "pack f f f")
REO = p.msg(20, 940, "\\$3 \\$1 \\$2")
RTS = p.obj(20, 900, "route 0 1")
TILT_UNP = p.obj(940, 1020, "unpack f f f")
p.connect(IN0, 0, RIN0, 0)
p.connect(RIN0, 0, UNP, 0)
p.connect(UNP, 2, PK, 2)
p.connect(UNP, 1, PK, 1)
p.connect(UNP, 0, PK, 0)
p.connect(PK, 0, REO, 0)
p.connect(REO, 0, RTS, 0)
p.connect(RIN0, 2, TILT_UNP, 0)
p.connect(TILT_UNP, 2, ZT, 0)
p.connect(TILT_UNP, 1, YT, 0)
p.connect(TILT_UNP, 0, XT, 0)

# ---------------- calibrate ----------------
# any press (or bare center) snapshots raw holds into dev colds, prints the
# center, then recomputes px/py/h from zero-deviation so the bubble jumps home.
CAL_T = p.obj(640, 900, "t b b b b b")
CPK = p.obj(640, 860, "pack f f f")
CMS = p.msg(640, 820, "center \\$1 \\$2 \\$3")
MSG0 = p.msg(760, 900, "0")
p.connect(RTS, 1, CAL_T, 0)
p.connect(RIN0, 1, CAL_T, 0)
p.connect(CAL_T, 4, TZH, 0)
p.connect(TZH, 0, CPK, 2)
p.connect(CAL_T, 3, TYH, 0)
p.connect(TYH, 0, CPK, 1)
p.connect(TYH, 0, DEVY, 1)
p.connect(CAL_T, 2, TXH, 0)
p.connect(TXH, 0, CPK, 0)
p.connect(TXH, 0, DEVX, 1)
p.connect(CPK, 0, CMS, 0)
p.connect(CMS, 0, OUT_INFO, 0)
p.connect(CAL_T, 1, MSG0, 0)
p.connect(MSG0, 0, PXEXPR, 0)
p.connect(MSG0, 0, PYEXPR, 0)
p.connect(MSG0, 0, MAGEXPR, 1)
p.connect(MSG0, 0, MAGEXPR, 0)

# ---------------- init ----------------
CINIT = p.obj(900, 200, "loadbang")
C127 = p.msg(960, 200, "127")
p.connect(CINIT, 0, C127, 0)
p.connect(C127, 0, TXH, 1)
p.connect(C127, 0, TXH2, 1)
p.connect(C127, 0, TYH, 1)
p.connect(C127, 0, TZH, 1)
p.connect(C127, 0, DEVX, 1)
p.connect(C127, 0, DEVY, 1)

p.write("../../patchers/tiltvis.pd")
print("wrote tiltvis.pd:", len(p.objs), "objects,", len(p.conns), "connections")
