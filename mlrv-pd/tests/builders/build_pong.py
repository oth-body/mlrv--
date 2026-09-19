#!/usr/bin/env python3
"""Builder for mlrv-pd/patchers/pong.pd (8x8 monome-grid Pong).

Pure-vanilla-Pd game logic reusing mlrv-pd's proven I/O seam:
  serialosc.pd outlet 1 (grid keys "x y state") -> pong inlet 0
  pong outlet 0 (LED "x y level") -> grid.pd -> serialosc.pd LED inlet
Protocol, controls, and levels are documented in the header comment
written into the patch itself.

Wiring discipline: a [float] outlet fans out ONLY to silent store
inlets. Every value read at N different times lives in N physical
[float] copies; each copy has exactly one outlet connection, so a
read can never trigger an unintended chain. Broadcast writes (one
source -> many silent inlets) are always safe.

Run from this directory:  python3 build_pong.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1400, h=1100)

p.text(20, 20,
    "pong.pd: 8x8 monome-grid pong for a greyscale/varibright 64 (levels 0-15) \\, "
    "built on mlrv-pd's serialosc.pd + grid.pd primitives. inlet 0 takes grid keys "
    "(list x y state \\, same shape serialosc.pd emits) plus direct messages: "
    "serve <vx> <vy> (deterministic serve) \\, reset \\, tick (single physics step -- "
    "same entry as the metro). creation arg \\$1 = tick ms (required \\, e.g. 130). "
    "outlet 0 = LED triples x y level: paddles 10 \\, ball 15 \\, 1-frame trail 4 \\, "
    "center net dots 2. outlet 1 = score/game/reset lines. controls: press x=0 sets left "
    "paddle row (clamped 1..6 \\, 3-tall) \\, x=7 sets right paddle \\, x=3|4 + y=0 resets \\, "
    "any press serves while waiting. first to 7 wins \\, scores auto-reset. "
    "NOTE (wiring): per-site [float] copies -- each copy has exactly one outlet "
    "connection. verified: tests/run_pong_test.sh.")
p.text(20, 100,
    "copies: GBX/GBY x4 (shift comp sync ball) \\, GVX x1 \\, GVY x2 (comp flip) \\, "
    "GLP/GRP x1 \\, GWAIT x2 (tick serve) \\, GSL/GSR x1 \\, GPBX/GPBY x3 (rw erase trail) \\, "
    "GPPBX/GPPBY x1 \\, GOFFL/GOFFR x1 \\, GNX x3 (edge mid side) \\, GNY x3 (difL difR store) \\, "
    "GYST x3 (left right mid).")

IN0 = p.obj(20, 160, "inlet")
OUT_LED = p.obj(20, 1020, "outlet")
OUT_INFO = p.obj(200, 1020, "outlet")

# ---------------- state (per-site copies) ----------------
GBX = [p.obj(300 + i * 55, 200, "float 3") for i in range(4)]
GBY = [p.obj(540 + i * 55, 200, "float 3") for i in range(4)]
GVX = [p.obj(780, 200, "float 0")]
GVY = [p.obj(840 + i * 55, 200, "float 0") for i in range(2)]
GLP = [p.obj(960, 200, "float 3")]
GRP = [p.obj(1020, 200, "float 3")]
GWAIT = [p.obj(1080 + i * 55, 200, "float 1") for i in range(2)]
GSL = [p.obj(1200, 200, "float 0")]
GSR = [p.obj(1260, 200, "float 0")]
GPBX = [p.obj(300 + i * 55, 240, "float 3") for i in range(3)]
GPBY = [p.obj(540 + i * 55, 240, "float 3") for i in range(3)]
GPPBX = [p.obj(780, 240, "float 3")]
GPPBY = [p.obj(840, 240, "float 3")]
GOFFL = [p.obj(900, 240, "float 0")]
GOFFR = [p.obj(960, 240, "float 0")]
GNX = [p.obj(1020 + i * 55, 240, "float 3") for i in range(3)]
GNY = [p.obj(1140 + i * 55, 240, "float 3") for i in range(3)]
GYST = [p.obj(1320, 240, "float 0"), p.obj(1320, 275, "float 0"),
        p.obj(1320, 310, "float 0")]


def w(src, sout, copies):
    for c in copies:
        p.connect(src, sout, c, 1)


# ---------------- diff / score-pack block ----------------
DIFFL = p.obj(300, 300, "expr \\$f1-\\$f2")
DIFL_T = p.obj(300, 340, "t f f")
ABSL = p.obj(300, 380, "abs")
MOSHITL = p.obj(300, 420, "moses 2")
DIFFR = p.obj(420, 300, "expr \\$f1-\\$f2")
DIFR_T = p.obj(420, 340, "t f f")
ABSR = p.obj(420, 380, "abs")
MOSHITR = p.obj(420, 420, "moses 2")
SCPK = p.obj(720, 300, "pack f f")
PRE_SCORE = p.msg(720, 340, "score \\$1 \\$2")
p.connect(PRE_SCORE, 0, OUT_INFO, 0)
p.connect(DIFFL, 0, DIFL_T, 0)
p.connect(DIFL_T, 1, GOFFL[0], 1)
p.connect(DIFL_T, 0, ABSL, 0)
p.connect(ABSL, 0, MOSHITL, 0)
p.connect(DIFFR, 0, DIFR_T, 0)
p.connect(DIFR_T, 1, GOFFR[0], 1)
p.connect(DIFR_T, 0, ABSR, 0)
p.connect(ABSR, 0, MOSHITR, 0)
p.connect(SCPK, 0, PRE_SCORE, 0)
DPLB = p.obj(300, 260, "loadbang")
DPLB3 = p.msg(360, 260, "3")
p.connect(DPLB, 0, DPLB3, 0)
p.connect(DPLB3, 0, DIFFL, 1)
p.connect(DPLB3, 0, DIFFR, 1)

# ---------------- render ----------------
RENDER_IN = p.obj(20, 960, "t b b b b b b")
EPP_T = p.obj(60, 910, "t b b")
PKPP = p.obj(60, 870, "pack f f")
MPP = p.msg(60, 830, "\\$1 \\$2 0")
EP_T = p.obj(200, 910, "t b b")
PKP = p.obj(200, 870, "pack f f")
MPE = p.msg(200, 830, "\\$1 \\$2 0")
NET_T = p.obj(340, 910, "t b b b b b b b b")
NETM = [p.msg(340 + i * 45, 830, m) for i, m in enumerate(
    ["3 0 2", "4 0 2", "3 2 2", "4 2 2", "3 4 2", "4 4 2", "3 6 2", "4 6 2"])]
PR_T = p.obj(700, 910, "t b b")
LP_T = p.obj(700, 870, "t f f f")
LM1 = p.obj(700, 830, "- 1")
ML1 = p.msg(700, 790, "0 \\$1 10")
ML2 = p.msg(760, 790, "0 \\$1 10")
LP1 = p.obj(820, 830, "+ 1")
ML3 = p.msg(820, 790, "0 \\$1 10")
RP_T = p.obj(940, 870, "t f f f")
RM1 = p.obj(940, 830, "- 1")
MR1 = p.msg(940, 790, "7 \\$1 10")
MR2 = p.msg(1000, 790, "7 \\$1 10")
RP1 = p.obj(1060, 830, "+ 1")
MR3 = p.msg(1060, 790, "7 \\$1 10")
TRAIL_T = p.obj(1140, 910, "t b b")
PKT = p.obj(1140, 870, "pack f f")
MTR = p.msg(1140, 830, "\\$1 \\$2 4")
BALL_T = p.obj(1260, 910, "t b b")
PKB = p.obj(1260, 870, "pack f f")
MBL = p.msg(1260, 830, "\\$1 \\$2 15")

p.connect(RENDER_IN, 5, EPP_T, 0)
p.connect(EPP_T, 1, GPPBY[0], 0)
p.connect(GPPBY[0], 0, PKPP, 1)
p.connect(EPP_T, 0, GPPBX[0], 0)
p.connect(GPPBX[0], 0, PKPP, 0)
p.connect(PKPP, 0, MPP, 0)
p.connect(MPP, 0, OUT_LED, 0)
p.connect(RENDER_IN, 4, EP_T, 0)
p.connect(EP_T, 1, GPBY[1], 0)
p.connect(GPBY[1], 0, PKP, 1)
p.connect(EP_T, 0, GPBX[1], 0)
p.connect(GPBX[1], 0, PKP, 0)
p.connect(PKP, 0, MPE, 0)
p.connect(MPE, 0, OUT_LED, 0)
p.connect(RENDER_IN, 3, NET_T, 0)
for i, m in enumerate(NETM):
    p.connect(NET_T, i, m, 0)
    p.connect(m, 0, OUT_LED, 0)
p.connect(RENDER_IN, 2, PR_T, 0)
p.connect(PR_T, 1, GLP[0], 0)
p.connect(GLP[0], 0, LP_T, 0)
p.connect(LP_T, 2, LM1, 0)
p.connect(LM1, 0, ML1, 0)
p.connect(ML1, 0, OUT_LED, 0)
p.connect(LP_T, 1, ML2, 0)
p.connect(ML2, 0, OUT_LED, 0)
p.connect(LP_T, 0, LP1, 0)
p.connect(LP1, 0, ML3, 0)
p.connect(ML3, 0, OUT_LED, 0)
p.connect(PR_T, 0, GRP[0], 0)
p.connect(GRP[0], 0, RP_T, 0)
p.connect(RP_T, 2, RM1, 0)
p.connect(RM1, 0, MR1, 0)
p.connect(MR1, 0, OUT_LED, 0)
p.connect(RP_T, 1, MR2, 0)
p.connect(MR2, 0, OUT_LED, 0)
p.connect(RP_T, 0, RP1, 0)
p.connect(RP1, 0, MR3, 0)
p.connect(MR3, 0, OUT_LED, 0)
p.connect(RENDER_IN, 1, TRAIL_T, 0)
p.connect(TRAIL_T, 1, GPBY[2], 0)
p.connect(GPBY[2], 0, PKT, 1)
p.connect(TRAIL_T, 0, GPBX[2], 0)
p.connect(GPBX[2], 0, PKT, 0)
p.connect(PKT, 0, MTR, 0)
p.connect(MTR, 0, OUT_LED, 0)
p.connect(RENDER_IN, 0, BALL_T, 0)
p.connect(BALL_T, 1, GBY[3], 0)
p.connect(GBY[3], 0, PKB, 1)
p.connect(BALL_T, 0, GBX[3], 0)
p.connect(GBX[3], 0, PKB, 0)
p.connect(PKB, 0, MBL, 0)
p.connect(MBL, 0, OUT_LED, 0)

# ---------------- spawn / reset ----------------
SPAWN = p.obj(200, 460, "t b b b b b")
SPBX = p.msg(200, 500, "3")
SPBY = p.msg(260, 500, "3")
SPVX = p.msg(320, 500, "0")
SPVY = p.msg(380, 500, "0")
SPW = p.msg(440, 500, "1")
p.connect(SPAWN, 4, SPBX, 0)
w(SPBX, 0, GBX)
p.connect(SPBX, 0, GPBX[0], 1)
p.connect(SPBX, 0, GPBX[1], 1)
p.connect(SPBX, 0, GPBX[2], 1)
p.connect(SPBX, 0, GPPBX[0], 1)
p.connect(SPAWN, 3, SPBY, 0)
w(SPBY, 0, GBY)
p.connect(SPBY, 0, GPBY[0], 1)
p.connect(SPBY, 0, GPBY[1], 1)
p.connect(SPBY, 0, GPBY[2], 1)
p.connect(SPBY, 0, GPPBY[0], 1)
p.connect(SPAWN, 2, SPVX, 0)
p.connect(SPVX, 0, GVX[0], 1)
p.connect(SPAWN, 1, SPVY, 0)
w(SPVY, 0, GVY)
p.connect(SPAWN, 0, SPW, 0)
w(SPW, 0, GWAIT)

RESET_ALL = p.obj(200, 600, "t b b b b b b")
RSTMSG = p.msg(200, 640, "reset")
SLZ = p.msg(260, 640, "0")
SLZT = p.obj(260, 680, "t f f")
SRZ = p.msg(320, 640, "0")
SRZT = p.obj(320, 680, "t f f")
MID3 = p.msg(380, 640, "3")
PCT = p.obj(380, 680, "t f f f f")
p.connect(RESET_ALL, 5, RSTMSG, 0)
p.connect(RSTMSG, 0, OUT_INFO, 0)
p.connect(RESET_ALL, 4, SLZ, 0)
p.connect(SLZ, 0, SLZT, 0)
p.connect(SLZT, 1, GSL[0], 1)
p.connect(SLZT, 0, SCPK, 1)
p.connect(RESET_ALL, 3, SRZ, 0)
p.connect(SRZ, 0, SRZT, 0)
p.connect(SRZT, 1, GSR[0], 1)
p.connect(SRZT, 0, SCPK, 0)   # hot: emits score 0 0
p.connect(RESET_ALL, 2, MID3, 0)
p.connect(MID3, 0, PCT, 0)
p.connect(PCT, 3, GLP[0], 1)
p.connect(PCT, 2, DIFFL, 1)
p.connect(PCT, 1, GRP[0], 1)
p.connect(PCT, 0, DIFFR, 1)
p.connect(RESET_ALL, 1, SPAWN, 0)
p.connect(RESET_ALL, 0, RENDER_IN, 0)

# ---------------- tick + init ----------------
LB = p.obj(20, 220, "loadbang")
INIT_T = p.obj(20, 260, "t b b")
MSTART = p.msg(20, 300, "1")
METRO = p.obj(20, 340, "metro \\$1")
T_TICK = p.obj(20, 380, "t b b")
SELW = p.obj(20, 420, "sel 1")
p.connect(LB, 0, INIT_T, 0)
p.connect(INIT_T, 1, RESET_ALL, 0)
p.connect(INIT_T, 0, MSTART, 0)
p.connect(MSTART, 0, METRO, 0)
p.connect(METRO, 0, T_TICK, 0)
p.connect(T_TICK, 1, GWAIT[0], 0)
p.connect(GWAIT[0], 0, SELW, 0)

# ---------------- physics ----------------
SHIFT_T = p.obj(20, 460, "t b b b b b")
# render only while playing: metro bangs immediately on start (probe-verified)
# and a waiting court is static -- idle re-renders would spam ~180 OSC msgs/s.
PLAY_T = p.obj(20, 430, "t b b")
p.connect(SELW, 1, PLAY_T, 0)
p.connect(PLAY_T, 1, SHIFT_T, 0)
p.connect(PLAY_T, 0, RENDER_IN, 0)
p.connect(SHIFT_T, 4, GPBX[0], 0)
p.connect(GPBX[0], 0, GPPBX[0], 1)
p.connect(SHIFT_T, 3, GPBY[0], 0)
p.connect(GPBY[0], 0, GPPBY[0], 1)
p.connect(SHIFT_T, 2, GBX[0], 0)
p.connect(GBX[0], 0, GPBX[0], 1)
p.connect(GBX[0], 0, GPBX[1], 1)
p.connect(GBX[0], 0, GPBX[2], 1)
p.connect(SHIFT_T, 1, GBY[0], 0)
p.connect(GBY[0], 0, GPBY[0], 1)
p.connect(GBY[0], 0, GPBY[1], 1)
p.connect(GBY[0], 0, GPBY[2], 1)

NX_T = p.obj(20, 500, "t b b")
PLUSX = p.obj(300, 500, "+")
NX_T2 = p.obj(300, 540, "t f f")
NY_T = p.obj(300, 580, "t b b")
PLUSY = p.obj(300, 620, "+")
WALL_T = p.obj(300, 660, "t f f f")
BOUNCEQ = p.obj(300, 700, "expr (\\$f1<0)||(\\$f1>7)")
SELB = p.obj(300, 740, "sel 1")
NEGVY = p.obj(360, 740, "* -1")
CLMAX = p.obj(420, 700, "max 0")
CLMIN = p.obj(420, 740, "min 7")
EDGE_TB = p.obj(300, 780, "t b")
EDGEQ = p.obj(420, 780, "expr (\\$f1<=0)||(\\$f1>=7)")
SELE = p.obj(420, 820, "sel 1")
MID_T = p.obj(420, 860, "t b b")
p.connect(SHIFT_T, 0, NX_T, 0)
p.connect(NX_T, 1, GVX[0], 0)
p.connect(GVX[0], 0, PLUSX, 1)
p.connect(NX_T, 0, GBX[1], 0)
p.connect(GBX[1], 0, PLUSX, 0)
p.connect(PLUSX, 0, NX_T2, 0)
w(NX_T2, 1, GNX)
p.connect(NX_T2, 0, NY_T, 0)
p.connect(NY_T, 1, GVY[0], 0)
p.connect(GVY[0], 0, PLUSY, 1)
p.connect(NY_T, 0, GBY[1], 0)
p.connect(GBY[1], 0, PLUSY, 0)
p.connect(PLUSY, 0, WALL_T, 0)
p.connect(WALL_T, 2, BOUNCEQ, 0)
p.connect(BOUNCEQ, 0, SELB, 0)
p.connect(SELB, 0, GVY[1], 0)
p.connect(GVY[1], 0, NEGVY, 0)
w(NEGVY, 0, GVY)
p.connect(WALL_T, 1, CLMAX, 0)
p.connect(CLMAX, 0, CLMIN, 0)
w(CLMIN, 0, GNY)
p.connect(WALL_T, 0, EDGE_TB, 0)
p.connect(EDGE_TB, 0, GNX[0], 0)
p.connect(GNX[0], 0, EDGEQ, 0)
p.connect(EDGEQ, 0, SELE, 0)
p.connect(SELE, 1, MID_T, 0)
p.connect(MID_T, 1, GNX[1], 0)
w(GNX[1], 0, GBX)
p.connect(MID_T, 0, GNY[2], 0)
w(GNY[2], 0, GBY)

MOSX = p.obj(540, 820, "moses 1")
# [sel] match outlet emits a bare bang (probe-verified), which moses rejects --
# so the side select re-reads NX from its own copy instead of using SELE's outlet.
p.connect(SELE, 0, GNX[2], 0)
p.connect(GNX[2], 0, MOSX, 0)

LEFT_T = p.obj(540, 860, "t b")
HITLEFT = p.obj(540, 900, "t b b b b")
MVX1 = p.msg(600, 900, "1")
MBX0 = p.msg(660, 900, "0")
p.connect(MOSX, 0, LEFT_T, 0)
p.connect(LEFT_T, 0, GNY[0], 0)
p.connect(GNY[0], 0, DIFFL, 0)
p.connect(MOSHITL, 0, HITLEFT, 0)
p.connect(HITLEFT, 3, GOFFL[0], 0)
w(GOFFL[0], 0, GVY)
p.connect(HITLEFT, 2, MVX1, 0)
p.connect(MVX1, 0, GVX[0], 1)
p.connect(HITLEFT, 1, GNY[2], 0)
p.connect(HITLEFT, 0, MBX0, 0)
w(MBX0, 0, GBX)

RIGHT_T = p.obj(760, 860, "t b")
HITRIGHT = p.obj(760, 900, "t b b b b")
MVX_1 = p.msg(820, 900, "-1")
MBX7 = p.msg(880, 900, "7")
p.connect(MOSX, 1, RIGHT_T, 0)
p.connect(RIGHT_T, 0, GNY[1], 0)
p.connect(GNY[1], 0, DIFFR, 0)
p.connect(MOSHITR, 0, HITRIGHT, 0)
p.connect(HITRIGHT, 3, GOFFR[0], 0)
w(GOFFR[0], 0, GVY)
p.connect(HITRIGHT, 2, MVX_1, 0)
p.connect(MVX_1, 0, GVX[0], 1)
p.connect(HITRIGHT, 1, GNY[2], 0)
p.connect(HITRIGHT, 0, MBX7, 0)
w(MBX7, 0, GBX)

# miss left edge -> SR+1 ; miss right edge -> SL+1
MISSR = p.obj(300, 460, "t b")
INC1 = p.obj(940, 500, "+ 1")
UPR_T = p.obj(940, 540, "t f f f")
WINR = p.obj(940, 580, "sel 7")
GAMER = p.obj(940, 620, "t b b b b")
GR_SLZ = p.msg(940, 660, "0")
GR_SLZT = p.obj(940, 700, "t f f")
GR_SRZ = p.msg(1000, 660, "0")
GR_SRZT = p.obj(1000, 700, "t f f")
GR_MSG = p.msg(1060, 660, "game R wins")
p.connect(MOSHITL, 1, MISSR, 0)
p.connect(MISSR, 0, GSR[0], 0)
p.connect(GSR[0], 0, INC1, 0)
p.connect(INC1, 0, UPR_T, 0)
p.connect(UPR_T, 2, GSR[0], 1)
p.connect(UPR_T, 1, SCPK, 0)   # hot: emits score SL SRnew
p.connect(UPR_T, 0, WINR, 0)
p.connect(WINR, 1, SPAWN, 0)
p.connect(WINR, 0, GAMER, 0)
p.connect(GAMER, 3, GR_SLZ, 0)
p.connect(GR_SLZ, 0, GR_SLZT, 0)
p.connect(GR_SLZT, 1, GSL[0], 1)
p.connect(GR_SLZT, 0, SCPK, 1)
p.connect(GAMER, 2, GR_SRZ, 0)
p.connect(GR_SRZ, 0, GR_SRZT, 0)
p.connect(GR_SRZT, 1, GSR[0], 1)
p.connect(GR_SRZT, 0, SCPK, 0)   # hot: emits score 0 0
p.connect(GAMER, 1, GR_MSG, 0)
p.connect(GR_MSG, 0, OUT_INFO, 0)
p.connect(GAMER, 0, SPAWN, 0)

MISSL = p.obj(420, 460, "t b")
INCL = p.obj(1120, 500, "+ 1")
UPL_T = p.obj(1120, 540, "t f f f")
WINL = p.obj(1120, 580, "sel 7")
ANL_T = p.obj(1120, 620, "t b b")
GAMEL = p.obj(1180, 620, "t b b b b")
GL_SLZ = p.msg(1180, 660, "0")
GL_SLZT = p.obj(1180, 700, "t f f")
GL_SRZ = p.msg(1240, 660, "0")
GL_SRZT = p.obj(1240, 700, "t f f")
GL_MSG = p.msg(1300, 660, "game L wins")
p.connect(MOSHITR, 1, MISSL, 0)
p.connect(MISSL, 0, GSL[0], 0)
p.connect(GSL[0], 0, INCL, 0)
p.connect(INCL, 0, UPL_T, 0)
p.connect(UPL_T, 2, GSL[0], 1)
p.connect(UPL_T, 1, SCPK, 1)   # cold: staged, bang below emits
p.connect(UPL_T, 0, WINL, 0)
p.connect(WINL, 1, ANL_T, 0)
p.connect(ANL_T, 1, SCPK, 0)   # bang hot inlet: emits score SLnew SR
p.connect(ANL_T, 0, SPAWN, 0)
p.connect(WINL, 0, GAMEL, 0)
p.connect(GAMEL, 3, GL_SLZ, 0)
p.connect(GL_SLZ, 0, GL_SLZT, 0)
p.connect(GL_SLZT, 1, GSL[0], 1)
p.connect(GL_SLZT, 0, SCPK, 1)
p.connect(GAMEL, 2, GL_SRZ, 0)
p.connect(GL_SRZ, 0, GL_SRZT, 0)
p.connect(GL_SRZT, 1, GSR[0], 1)
p.connect(GL_SRZT, 0, SCPK, 0)   # hot: emits score 0 0
p.connect(GAMEL, 1, GL_MSG, 0)
p.connect(GL_MSG, 0, OUT_INFO, 0)
p.connect(GAMEL, 0, SPAWN, 0)

# ---------------- input ----------------
RIN = p.obj(20, 640, "route list serve reset tick")
UNP = p.obj(20, 680, "unpack f f f")
PK = p.obj(20, 720, "pack f f f")
REO = p.msg(20, 760, "\\$3 \\$1 \\$2")
RTS = p.obj(20, 800, "route 0 1")
UNP2 = p.obj(20, 840, "unpack f f")
XRT = p.obj(20, 880, "route 0 7 3 4")
p.connect(IN0, 0, RIN, 0)
p.connect(RIN, 0, UNP, 0)
p.connect(UNP, 2, PK, 2)
p.connect(UNP, 1, PK, 1)
p.connect(UNP, 0, PK, 0)
p.connect(PK, 0, REO, 0)
p.connect(REO, 0, RTS, 0)
p.connect(RTS, 1, UNP2, 0)
p.connect(UNP2, 1, GYST[0], 1)
p.connect(UNP2, 1, GYST[1], 1)
p.connect(UNP2, 1, GYST[2], 1)
p.connect(UNP2, 0, XRT, 0)

# left paddle + serve/render
PL_T = p.obj(200, 880, "t b b")
CLL = p.obj(200, 840, "max 1")
CLL2 = p.obj(200, 800, "min 6")
SETL_T = p.obj(200, 760, "t f f")
PS_T = p.obj(260, 880, "t b b")
p.connect(XRT, 0, PL_T, 0)
p.connect(PL_T, 1, GYST[0], 0)
p.connect(GYST[0], 0, CLL, 0)
p.connect(CLL, 0, CLL2, 0)
p.connect(CLL2, 0, SETL_T, 0)
p.connect(SETL_T, 1, GLP[0], 1)
p.connect(SETL_T, 0, DIFFL, 1)
p.connect(PL_T, 0, PS_T, 0)
p.connect(PS_T, 1, GWAIT[1], 0)
p.connect(PS_T, 0, RENDER_IN, 0)

# right paddle + serve/render
PRP_T = p.obj(420, 880, "t b b")
CLR = p.obj(420, 840, "max 1")
CLR2 = p.obj(420, 800, "min 6")
SETR_T = p.obj(420, 760, "t f f")
PSR_T = p.obj(480, 880, "t b b")
p.connect(XRT, 1, PRP_T, 0)
p.connect(PRP_T, 1, GYST[1], 0)
p.connect(GYST[1], 0, CLR, 0)
p.connect(CLR, 0, CLR2, 0)
p.connect(CLR2, 0, SETR_T, 0)
p.connect(SETR_T, 1, GRP[0], 1)
p.connect(SETR_T, 0, DIFFR, 1)
p.connect(PRP_T, 0, PSR_T, 0)
p.connect(PSR_T, 1, GWAIT[1], 0)
p.connect(PSR_T, 0, RENDER_IN, 0)

# middle top (x=3|4): y==0 -> full reset ; other middle presses: serve/render
MIDP_T = p.obj(640, 880, "t b b")
SELR0 = p.obj(640, 840, "sel 0")
PMS_T = p.obj(700, 880, "t b b")
p.connect(XRT, 2, MIDP_T, 0)
p.connect(XRT, 3, MIDP_T, 0)
p.connect(MIDP_T, 1, GYST[2], 0)
p.connect(GYST[2], 0, SELR0, 0)
p.connect(SELR0, 0, RESET_ALL, 0)
p.connect(MIDP_T, 0, PMS_T, 0)
p.connect(PMS_T, 1, GWAIT[1], 0)
p.connect(PMS_T, 0, RENDER_IN, 0)

# other columns: serve/render
OTH_T = p.obj(820, 880, "t b b")
p.connect(XRT, 4, OTH_T, 0)
p.connect(OTH_T, 1, GWAIT[1], 0)
p.connect(OTH_T, 0, RENDER_IN, 0)

# grid-serve gate: only while waiting
SELSV = p.obj(200, 300, "sel 1")
DOSERVE = p.obj(200, 260, "t b b b")
RANDX = p.obj(260, 260, "random 2")
EX1 = p.obj(260, 220, "expr \\$f1*2-1")
RANDY = p.obj(320, 260, "random 3")
EM1 = p.obj(320, 220, "expr \\$f1-1")
W0G = p.msg(380, 260, "0")
PREVSYNC = p.obj(200, 380, "t b b")
SY1 = p.obj(200, 340, "t f f")
SY2 = p.obj(260, 340, "t f f")
p.connect(GWAIT[1], 0, SELSV, 0)
p.connect(SELSV, 0, DOSERVE, 0)
p.connect(DOSERVE, 2, RANDX, 0)
p.connect(RANDX, 0, EX1, 0)
p.connect(EX1, 0, GVX[0], 1)
p.connect(DOSERVE, 1, RANDY, 0)
p.connect(RANDY, 0, EM1, 0)
w(EM1, 0, GVY)
p.connect(DOSERVE, 0, W0G, 0)
p.connect(W0G, 0, GWAIT[0], 1)
p.connect(W0G, 0, GWAIT[1], 1)
p.connect(W0G, 0, PREVSYNC, 0)
p.connect(PREVSYNC, 1, GBX[2], 0)
p.connect(GBX[2], 0, SY1, 0)
p.connect(SY1, 1, GPBX[0], 1)
p.connect(SY1, 1, GPBX[1], 1)
p.connect(SY1, 1, GPBX[2], 1)
p.connect(SY1, 0, GPPBX[0], 1)
p.connect(PREVSYNC, 0, GBY[2], 0)
p.connect(GBY[2], 0, SY2, 0)
p.connect(SY2, 1, GPBY[0], 1)
p.connect(SY2, 1, GPBY[1], 1)
p.connect(SY2, 1, GPBY[2], 1)
p.connect(SY2, 0, GPPBY[0], 1)

# deterministic serve: serve <vx> <vy>
SUV = p.obj(940, 680, "unpack f f")
SV2_T = p.obj(940, 720, "t f b b")
W0E = p.msg(940, 760, "0")
p.connect(RIN, 1, SUV, 0)
p.connect(SUV, 1, GVY[0], 1)
p.connect(SUV, 1, GVY[1], 1)
p.connect(SUV, 0, SV2_T, 0)
p.connect(SV2_T, 2, W0E, 0)
p.connect(W0E, 0, GWAIT[0], 1)
p.connect(W0E, 0, GWAIT[1], 1)
p.connect(SV2_T, 1, PREVSYNC, 0)
p.connect(SV2_T, 0, GVX[0], 1)

# reset + tick messages
p.connect(RIN, 2, RESET_ALL, 0)
p.connect(RIN, 3, T_TICK, 0)

p.write("../../patchers/pong.pd")
print("wrote pong.pd:", len(p.objs), "objects,", len(p.conns), "connections")
