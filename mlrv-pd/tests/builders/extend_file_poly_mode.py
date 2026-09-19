#!/usr/bin/env python3
"""Extend file_poly.pd: `mode <voice 1-4> <loop|shot>` (per-voice sample
parameters wiring item, mirroring the existing `gain <voice> <value>` /
`pitch <voice> <semitones>` dispatch built by extend_file_poly_gain_pitch.py
-- makes sample_voice~.pd's new `mode <loop|shot>` message, built and
verified in isolation, reachable through file_poly.pd's public interface).

One real difference from gain/pitch: the payload here is a SYMBOL
("loop"/"shot"), not a float, so the shared store-then-bang idiom uses
[symbol] (already used elsewhere in this same file for array-name
dispatch, e.g. the makefilename->symbol->"set $1" chain) instead of
[float 0]. Everything else mirrors gain/pitch's shape exactly: unpack
"voice modeSymbol" (right-to-left firing puts the symbol into the store's
cold inlet before voice fires last and triggers [route 1 2 3 4]; each
matching outlet's bare bang re-reads the stored symbol into that voice's
own "mode $1" message).

Appends objects + one in-place edit that changes no existing indices:
  - route line gains `mode` (new outlet 11) -- outlet 11 (the old reject)
    was unconnected to anything before this change (checked first, same
    as the gain/pitch script's own check), so nothing needed rewiring.

Refuses to run twice.
"""
import sys

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/file_poly.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

assert lines[0].startswith("#N canvas"), "unexpected header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert len(body) + len(conns) == len(lines) - 1, "unexpected line types present"

OLD_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch group groupstop;"
NEW_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch group groupstop mode;"
if NEW_ROUTE in body:
    sys.exit("already extended -- refusing to double-append")
assert body.count(OLD_ROUTE) == 1, "route line not found exactly once -- run extend_file_poly_gain_pitch.py first"

ROUTE_IDX = body.index(OLD_ROUTE)
assert ROUTE_IDX == 9, f"route index moved: {ROUTE_IDX}"
assert not any(c.startswith(f"#X connect {ROUTE_IDX} 11 ") for c in conns), \
    "route outlet 11 (old reject) already connected -- design assumption broken"
assert body[75] == "#X obj 460 760 sample_voice~ mlrv-sample-0;", f"voice1 moved: {body[75]}"
assert body[76] == "#X obj 460 820 sample_voice~ mlrv-sample-1;", f"voice2 moved: {body[76]}"
assert body[77] == "#X obj 460 880 sample_voice~ mlrv-sample-2;", f"voice3 moved: {body[77]}"
assert body[78] == "#X obj 460 940 sample_voice~ mlrv-sample-3;", f"voice4 moved: {body[78]}"
VOICE_OBJS = [75, 76, 77, 78]
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

BASE_Y = 2500
UNP = obj(20, BASE_Y, "unpack f s")
STORE = obj(20, BASE_Y + 50, "symbol")
VROUTE = obj(20, BASE_Y + 100, "route 1 2 3 4")
connect(ROUTE_IDX, 11, UNP, 0)
connect(UNP, 1, STORE, 1)   # modeSymbol (2nd atom) fires first (right-to-left), sets cold
connect(UNP, 0, VROUTE, 0)  # voice (1st atom) fires last, triggers the dispatch
for i in range(4):
    BANG_STORE = obj(160 + 100 * i, BASE_Y + 100, "t b")
    MSG = msg(160 + 100 * i, BASE_Y + 150, "mode \\$1")
    connect(VROUTE, i, BANG_STORE, 0)
    connect(BANG_STORE, 0, STORE, 0)
    connect(STORE, 0, MSG, 0)
    connect(MSG, 0, VOICE_OBJS[i], 0)

text(20, BASE_Y + 200,
     "mode <voice 1-4> <loop|shot> (route outlet 11) -- 2026-09-18 per-voice sample "
     "parameters wiring item, mirrors gain/pitch's dispatch exactly (extend_file_poly_gain_pitch.py) "
     "except the payload is a SYMBOL (loop/shot) \\, not a float \\, so the shared store uses "
     "[symbol] instead of [float 0] -- same store-then-bang idiom already used elsewhere in this "
     "file for array-name dispatch (makefilename->symbol->\"set $1\"). This file does no logic on "
     "the mode value itself \\, only dispatch -- the actual shot-mode duration-timer machinery "
     "lives entirely in sample_voice~.pd. Route's outlet 11 (old reject) was unconnected to anything "
     "before this change \\, confirmed by reading the file first. Not yet reachable from mapping.pd "
     "or any grid gesture -- see the Per-Voice Sample Parameters doc.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
