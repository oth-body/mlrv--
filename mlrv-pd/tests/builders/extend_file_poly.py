#!/usr/bin/env python3
"""Extend file_poly.pd: `unload <slot>` + `query` (sample-memory item).

Appends objects + connections; two in-place edits that change no indices:
  - route line gains `unload` (outlet 5) + `query` (outlet 6)
  - load-report pack outlet re-routed through a [t a a] (report + frame-store tap)
  - unload holder outlet re-routed through a [t a a] (report + frame-store tap)

Occupancy model: [table mlrv-fplen 8] tracks last-loaded frames per slot
(zero = empty). load stores soundfiler's reported frames; unload stores 0;
query dumps the tracked values ascending as `loaded <slot> <frames>`.
Tracked-store (not live [array size]) so unload+query can never resurrect a
slot in consumers (mapping.pd stores whatever the info outlet emits).

Unload mechanics: resize-1 / tabwrite-set / zero-cell-0 / resize-64, because
shrinking retains cell values and growing zero-fills (both probed 2026-09-18)
-- resize alone never silences anything. Dynamic `\; $1 resize N` sends only
work when $1 arrives as a proper symbol-message ([symbol] output); a bare
symbol fails with "$1: not enough arguments" (probed). Gate 0..7 via
[route 0 1 2 3 4 5 6 7] + static number msgs (bare floats into route emit
bangs, number recovered statically); out-of-range hits reject, ignored.
Hot-inlet order everywhere: last-arriving value on the hot inlet, msg-swap
restores output order (gotcha 15). Refuses to run twice.
"""
import sys

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/file_poly.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

assert lines[0].startswith("#N canvas"), "unexpected header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert len(body) + len(conns) == len(lines) - 1, "unexpected line types present"

OLD_ROUTE = "#X obj 20 130 route load play playv stop stopall;"
NEW_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query;"
if NEW_ROUTE in body:
    sys.exit("already extended -- refusing to double-append")
assert body.count(OLD_ROUTE) == 1, "route line not found exactly once"

ROUTE_IDX = body.index(OLD_ROUTE)
assert ROUTE_IDX == 9, f"route index moved: {ROUTE_IDX}"
assert body[21] == "#X obj 140 660 outlet;", f"info outlet moved: {body[21]}"
assert body[19] == "#X obj 140 550 pack f f;", f"load pack moved: {body[19]}"
assert body[20] == "#X msg 140 600 loaded \\$1 \\$2;", f"load msg moved: {body[20]}"
assert "#X connect 19 0 20 0;" in conns, "load pack->msg connect missing"
INFO_IDX = 21
body[ROUTE_IDX] = NEW_ROUTE

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

Y = 1450
# --- occupancy store (must exist before anything references it; position cosmetic) ---
T_FPLEN = obj(700, Y, "table mlrv-fplen 8")
TW_FPLEN = obj(700, Y + 60, "tabwrite mlrv-fplen")

# --- load-path frame-store tap: pack(19) -> T_LOAD -> msg(20) + L_SWAP -> TW_FPLEN ---
T_LOAD = obj(140, Y, "t a a")
L_SWAP = msg(260, Y, "\\$2 \\$1")
connect(T_LOAD, 1, 20, 0)
connect(T_LOAD, 0, L_SWAP, 0)
connect(L_SWAP, 0, TW_FPLEN, 0)

# --- unload section ---
U_ROUTE = obj(20, Y + 60, "route 0 1 2 3 4 5 6 7")
U_MSG = [msg(60 + 80 * i, Y + 110, str(i)) for i in range(8)]
U_TFF = obj(60, Y + 160, "t f f")
U_HOLD = obj(60, Y + 200, "float")
U_MK = obj(220, Y + 160, "makefilename mlrv-sample-%d")
U_SYM = obj(220, Y + 200, "symbol")
U_FAN = obj(220, Y + 240, "t b a a a a")
U_RS1 = msg(60, Y + 290, "\\; \\$1 resize 1")
U_SET = msg(200, Y + 290, "set \\$1")
U_ZERO = msg(340, Y + 290, "0 0")
U_RS64 = msg(480, Y + 290, "\\; \\$1 resize 64")
U_TW = obj(200, Y + 330, "tabwrite")
U_TEE = obj(60, Y + 240, "t a a")
U_REP = msg(60, Y + 340, "loaded \\$1 0")
U_STORE = msg(320, Y + 340, "0 \\$1")

connect(ROUTE_IDX, 5, U_ROUTE, 0)
for i in range(8):
    connect(U_ROUTE, i, U_MSG[i], 0)
    connect(U_MSG[i], 0, U_TFF, 0)
connect(U_TFF, 1, U_HOLD, 1)
connect(U_TFF, 0, U_MK, 0)
connect(U_MK, 0, U_SYM, 0)
connect(U_SYM, 0, U_FAN, 0)
connect(U_FAN, 4, U_RS1, 0)
connect(U_FAN, 3, U_SET, 0)
connect(U_SET, 0, U_TW, 0)
connect(U_FAN, 2, U_ZERO, 0)
connect(U_ZERO, 0, U_TW, 0)
connect(U_FAN, 1, U_RS64, 0)
connect(U_FAN, 0, U_HOLD, 0)
connect(U_HOLD, 0, U_TEE, 0)
connect(U_TEE, 1, U_REP, 0)
connect(U_TEE, 0, U_STORE, 0)
connect(U_REP, 0, INFO_IDX, 0)
connect(U_STORE, 0, TW_FPLEN, 0)

# --- query section: live tracked occupancy, ascending ---
QY = Y + 390
Q_FAN = obj(20, QY, "t b b b b b b b b")
connect(ROUTE_IDX, 6, Q_FAN, 0)
for s in range(8):
    x = 60 + 100 * s
    MSLOT = msg(x, QY + 50, str(s))
    T2 = obj(x, QY + 100, "t f f")
    TR = obj(x + 50, QY + 100, "tabread mlrv-fplen")
    PK = obj(x, QY + 150, "pack f f")
    MQ = msg(x, QY + 190, "loaded \\$2 \\$1")
    connect(Q_FAN, 7 - s, MSLOT, 0)
    connect(MSLOT, 0, T2, 0)
    connect(T2, 1, PK, 1)     # slot stored cold first
    connect(T2, 0, TR, 0)     # ...then frames arrive hot
    connect(TR, 0, PK, 0)
    connect(PK, 0, MQ, 0)
    connect(MQ, 0, INFO_IDX, 0)

text(20, QY + 250,
     "unload <slot> (route outlet 5) \\, query (outlet 6) -- 2026-09-18 sample-memory item. "
     "mlrv-fplen tracks last-loaded frames per slot (0 = empty\\, table inits 0). "
     "unload gates 0..7 (out-of-range ignored) then resize-1 / set / zero-cell-0 / resize-64 "
     "(grow zero-fills \\, shrink retains -- resize alone never silences) \\, stores 0 \\, reports "
     "loaded <slot> 0 so mapping.pd auto-marks the slot empty. "
     "query dumps tracked occupancy ascending. "
     "dynamic \\; \\$1 sends need symbol-wrapped names (bare symbols fail \\$1 substitution) -- all probed first.")

# re-route load pack outlet through the store tap (replaces old direct connect)
conns = [c for c in conns if c != "#X connect 19 0 20 0;"]
connect(19, 0, T_LOAD, 0)

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects (1 old connect replaced)")
