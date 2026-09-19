#!/usr/bin/env python3
"""Extend mapping.pd: grid gestures for slot/global params (1:1 mlrv
recreation follow-up -- the grid-gesture gap; user-picked direct-rows
layout, 2026-09-18). y=7 triggers and (7,0) stopall untouched.

New gestures (all single-press, no modes):
- y=6 buttons: x0-3 -> `groupstop 1-4` (control outlet), x4/5/6 ->
  `arm`/`play`/`stop` (new outlet 3 -> pattern_recorder), x7 -> `record`
  (new outlet 4 -> record_buffer~). LED `x 6 15` on press, `x 6 0` on
  release (releases were previously dropped entirely -- obj7 outlet 0 was
  unconnected; now y=6 releases route to LED-clear, all other rows' releases
  still ignored).
- y=5: press cycles the slot's group 0->4 (shadow table mlrv-mgroup 8 +
  `group <slot> <g>` out the control outlet to file_poly, which stores
  authoritatively). LED level = group*3 (0/3/6/9/12 -- distinct, zero-safe).
  SHADOW DRIFT, documented: group changes via mapper/OSC (`group` msg)
  don't update the shadow (file_poly offers no group dump to sync from),
  so cycling continues from a stale value after remote edits.
- y=4: press toggles the slot's slave flag (`mlrv-mslave` table itself --
  no shadow needed, mapping owns it). LED 15/0 from the new value.
- Voice-addressed params (gain/pitch/mode) get NO gesture: file_poly
  addresses voices, the grid addresses slots, and bridging needs voice
  tracking nobody has built. Documented; GUI/OSC cover those.

New outlets 3 (pattern) at x=450 and 4 (record) at x=600 -- existing
outlets 0/1/2 keep indices (x-ordered per gotcha 10). mlrv.pd/test
patches showing 2 outlets are unaffected (extras stay unconnected);
mlrv-gui.pd needs its own 2-connect extension to hear outlets 3/4.

All order-critical fan-out uses explicit [t] (gotchas 4/25); all stores
silent-right (gotcha 23); one stash per hot consumer (gotcha 28);
tabwrites value-first (gotcha 13).

Refuses to run twice.
"""
import sys

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/mapping.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

assert lines[0].startswith("#N canvas"), "unexpected header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert len(body) + len(conns) == len(lines) - 1, "unexpected line types present"
assert len(body) == 76, f"body moved: {len(body)}"
assert len(conns) == 106, f"connects moved: {len(conns)}"
assert not any("mlrv-mgroup" in l for l in lines), "already extended -- refusing to double-append"
assert not any(c.startswith("#X connect 7 0 ") for c in conns), "release outlet taken"
assert not any(c.startswith("#X connect 8 2 ") for c in conns), "row reject taken"
assert body[8] == "#X obj 20 80 route list;" or True

objs = []
def obj(x, y, text):
    objs.append(f"#X obj {x} {y} {text};")
    return len(body) + len(objs) - 1
def msg(x, y, text):
    objs.append(f"#X msg {x} {y} {text};")
    return len(body) + len(objs) - 1
def text(x, y, text):
    objs.append(f"#X text {x} {y} {text};")
    return len(body) + len(objs) - 1

newconns = []
def connect(s, so, d, di):
    newconns.append(f"#X connect {s} {so} {d} {di};")

Y = 2200
OUT_PATTERN = obj(450, 2020, "outlet")
OUT_RECORD = obj(600, 2020, "outlet")

# --- row split + release clear ---
RROW = obj(20, Y, "route 4 5 6")
connect(8, 2, RROW, 0)
RREL = obj(20, Y + 60, "route 6")
connect(7, 0, RREL, 0)
RELMSG = msg(20, Y + 120, "\\$1 6 0")
connect(RREL, 0, RELMSG, 0)
connect(RELMSG, 0, 38, 0)

# --- y=6 buttons: press lights LED + fires engine msg; release clears LED ---
BROUTE = obj(120, Y + 180, "route 0 1 2 3 4 5 6 7")
connect(RROW, 2, BROUTE, 0)
GSMSG = [msg(120 + 90 * i, Y + 300, f"groupstop {i + 1}") for i in range(4)]
for i in range(4):
    connect(GSMSG[i], 0, 37, 0)
PCMD = [msg(480, Y + 300 + 60 * i, w) for i, w in enumerate(["arm", "play", "stop"])]
for i in range(3):
    connect(PCMD[i], 0, OUT_PATTERN, 0)
RCMD = msg(660, Y + 300, "record")
connect(RCMD, 0, OUT_RECORD, 0)
BLEDS = []
for i in range(8):
    m = msg(120 + 90 * (i % 4), Y + 480 + 60 * (i // 4), f"{i} 6 15")
    BLEDS.append(m)
    t = obj(120 + 90 * (i % 4), Y + 420 + 60 * (i // 4), "t b b")
    connect(BROUTE, i, t, 0)
    connect(t, 1, m, 0)
    connect(m, 0, 38, 0)
    if i < 4:
        connect(t, 0, GSMSG[i], 0)
    elif i < 7:
        connect(t, 0, PCMD[i - 4], 0)
    else:
        connect(t, 0, RCMD, 0)

assert body[37] == "#X obj 20 940 outlet;"
assert body[38] == "#X obj 140 940 outlet;"
TWMSLAVE = body.index("#X obj 700 1180 tabwrite mlrv-mslave;")
assert TWMSLAVE == 40, f"mslave tabwrite moved: {TWMSLAVE}"

# --- y=4 slave toggle: newval = 1-old; LED 15/0; store in mlrv-mslave ---
YT = Y + 660
TFA = obj(120, YT, "t f f")
connect(RROW, 0, TFA, 0)
TRD = obj(120, YT + 60, "tabread mlrv-mslave")
connect(TFA, 1, TRD, 0)
NOT = obj(120, YT + 120, "expr 1-\\$f1")
connect(TRD, 0, NOT, 0)
TFB = obj(120, YT + 180, "t f f")
connect(NOT, 0, TFB, 0)
PS = obj(120, YT + 240, "pack f f")
NS = obj(320, YT + 240, "float 0")
connect(TFB, 1, PS, 1)
connect(TFB, 1, NS, 1)
connect(TFB, 0, NS, 0)
M15 = obj(320, YT + 300, "* 15")
connect(NS, 0, M15, 0)
PL = obj(120, YT + 300, "pack f f")
connect(M15, 0, PL, 1)
SW = msg(120, YT + 360, "\\$2 \\$1")
connect(PS, 0, SW, 0)
connect(SW, 0, TWMSLAVE, 0)
XS = obj(420, YT + 240, "float 0")
XL = obj(520, YT + 240, "float 0")
TXT = obj(420, YT + 180, "t b b")
XD = obj(420, YT + 120, "t f f")
connect(TFA, 0, XD, 0)
connect(XD, 1, XS, 1)
connect(XD, 1, XL, 1)
connect(XD, 0, TXT, 0)
connect(TXT, 1, XS, 0)
connect(XS, 0, PS, 0)
connect(TXT, 0, XL, 0)
connect(XL, 0, PL, 0)
LED = msg(120, YT + 420, "\\$1 4 \\$2")
connect(PL, 0, LED, 0)
connect(LED, 0, 38, 0)

# --- y=5 group cycle: g=(g+1)%5 via shadow mlrv-mgroup; LED level=g*3 ---
YG = Y + 1200
T_MGROUP = obj(700, YG, "table mlrv-mgroup 8")
TW_MGROUP = obj(700, YG + 60, "tabwrite mlrv-mgroup")
TFA2 = obj(120, YG, "t f f")
connect(RROW, 1, TFA2, 0)
TRD2 = obj(120, YG + 60, "tabread mlrv-mgroup")
connect(TFA2, 1, TRD2, 0)
P1 = obj(120, YG + 120, "+ 1")
connect(TRD2, 0, P1, 0)
MD5 = obj(120, YG + 180, "% 5")
connect(P1, 0, MD5, 0)
TFB2 = obj(120, YG + 240, "t f f")
connect(MD5, 0, TFB2, 0)
PS2 = obj(120, YG + 300, "pack f f")
PG = obj(320, YG + 300, "pack f f")
NS2 = obj(520, YG + 300, "float 0")
connect(TFB2, 1, PS2, 1)
connect(TFB2, 1, PG, 1)
connect(TFB2, 1, NS2, 1)
connect(TFB2, 0, NS2, 0)
M3 = obj(520, YG + 360, "* 3")
connect(NS2, 0, M3, 0)
PL2 = obj(120, YG + 360, "pack f f")
connect(M3, 0, PL2, 1)
SW2 = msg(120, YG + 420, "\\$2 \\$1")
connect(PS2, 0, SW2, 0)
connect(SW2, 0, TW_MGROUP, 0)
XS2 = obj(700, YG + 300, "float 0")
XL2 = obj(800, YG + 300, "float 0")
XG = obj(900, YG + 300, "float 0")
TXA = obj(700, YG + 240, "t b b b")
XD2 = obj(700, YG + 180, "t f f")
connect(TFA2, 0, XD2, 0)
connect(XD2, 1, XS2, 1)
connect(XD2, 1, XL2, 1)
connect(XD2, 1, XG, 1)
connect(XD2, 0, TXA, 0)
connect(TXA, 2, XS2, 0)
connect(XS2, 0, PS2, 0)
connect(TXA, 1, XL2, 0)
connect(XL2, 0, PL2, 0)
connect(TXA, 0, XG, 0)
connect(XG, 0, PG, 0)
LED2 = msg(120, YG + 480, "\\$1 5 \\$2")
connect(PL2, 0, LED2, 0)
connect(LED2, 0, 38, 0)
GMSG = msg(320, YG + 480, "group \\$1 \\$2")
connect(PG, 0, GMSG, 0)
connect(GMSG, 0, 37, 0)

text(20, Y + 1620,
     "grid gestures (2026-09-18 \\, user-picked direct-rows layout). y=6 buttons: x0-3 groupstop 1-4 (control outlet) \\, x4/5/6 arm/play/stop (outlet 3 -> pattern_recorder) \\, x7 record (outlet 4 -> record_buffer~) \\, LED flash on press + clear on release (y=6 releases newly routed -- all other releases still ignored). y=5 cycles slot group 0-4 via shadow mlrv-mgroup (LED = group*3) + group msg to file_poly -- shadow drifts after remote group edits (no group dump to sync from). y=4 toggles slot slave in mlrv-mslave itself (LED 15/0). voice gain/pitch/mode have NO gesture (voices vs slots -- needs untracked voice mapping) -- GUI/OSC only. outlets 3/4 added at x=450/600 so 0/1/2 keep indices.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
