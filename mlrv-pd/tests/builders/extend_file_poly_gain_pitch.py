#!/usr/bin/env python3
"""Extend file_poly.pd: `gain <voice 1-4> <value>` + `pitch <voice 1-4> <semitones>`
(per-voice sample parameters wiring item -- makes the sample_voice~.pd-level
gain/pitch messages, built and verified in isolation, reachable through
file_poly.pd's public interface).

Appends objects + one in-place edit that changes no existing indices:
  - route line gains `gain` (new outlet 7) + `pitch` (new outlet 8) --
    route's existing outlet 7 (reject) was unconnected to anything before
    this change (checked first), so nothing needed rewiring because of it.

Mirrors playv's existing per-voice dispatch idiom (unpack -> route 1 2 3 4
-> one reconstruction chain per voice) but simpler: gain/pitch don't need
per-voice array-name lookup, just "forward this one value to voice N's
sample_voice~ instance as <keyword> <value>". Design: unpack "voice value"
(right-to-left firing means value, the 2nd atom, lands in a shared [float]
store BEFORE voice, the 1st atom, arrives and fires the route dispatch --
same store-then-bang idiom sample_voice~.pd's own gain message already
uses). route 1 2 3 4 on the bare voice number outputs a bang on the
matching outlet (no trailing atoms to pass through); that bang re-emits
the stored value into a per-voice "<keyword> $1" message feeding the right
sample_voice~ instance directly. Shared factory function since gain and
pitch are structurally identical except for the keyword and creation-arg
seed value used for the store (both harmless either way here since the
store is always freshly set before being read -- 0 is used for both).

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

OLD_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query;"
NEW_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch;"
if NEW_ROUTE in body:
    sys.exit("already extended -- refusing to double-append")
assert body.count(OLD_ROUTE) == 1, "route line not found exactly once"

ROUTE_IDX = body.index(OLD_ROUTE)
assert ROUTE_IDX == 9, f"route index moved: {ROUTE_IDX}"
assert not any(c.startswith(f"#X connect {ROUTE_IDX} 7 ") for c in conns), \
    "route outlet 7 (old reject) already connected -- design assumption broken"
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

def build_dispatch(keyword, route_outlet, base_y):
    UNP = obj(20, base_y, "unpack f f")
    STORE = obj(20, base_y + 50, "float 0")
    VROUTE = obj(20, base_y + 100, "route 1 2 3 4")
    connect(ROUTE_IDX, route_outlet, UNP, 0)
    connect(UNP, 1, STORE, 1)   # value (2nd atom) fires first (right-to-left), sets cold
    connect(UNP, 0, VROUTE, 0)  # voice (1st atom) fires last, triggers the dispatch
    for i in range(4):
        BANG_STORE = obj(160 + 100 * i, base_y + 100, "t b")
        MSG = msg(160 + 100 * i, base_y + 150, f"{keyword} \\$1")
        connect(VROUTE, i, BANG_STORE, 0)
        connect(BANG_STORE, 0, STORE, 0)
        connect(STORE, 0, MSG, 0)
        connect(MSG, 0, VOICE_OBJS[i], 0)

build_dispatch("gain", 7, 1900)
build_dispatch("pitch", 8, 2100)

text(20, 2300,
     "gain <voice 1-4> <value> (route outlet 7) \\, pitch <voice 1-4> <semitones> (outlet 8) -- "
     "2026-09-18 per-voice sample parameters wiring item. Forwards a value to one of the 4 "
     "sample_voice~ instances' own gain/pitch messages (built and verified in isolation earlier "
     "this session) -- this file does no arithmetic on the value itself \\, it only dispatches it "
     "to the right voice. unpack's right-to-left firing (gotcha #4) puts the value (2nd atom) "
     "into a shared [float 0] store's COLD inlet before the voice (1st atom) fires "
     "[route 1 2 3 4] \\, whose matching outlet emits a bare bang (a lone number with nothing "
     "trailing it always does) that re-reads the already-stored value out into that voice's own "
     "\"<keyword> \\$1\" message. Route's old reject outlet (7) was unconnected to anything before "
     "gain/pitch were added as outlets 7/8 \\, confirmed by reading the file first \\, so nothing "
     "needed rewiring because of the outlet-count change. Not yet reachable from mapping.pd or "
     "any grid gesture -- see the Per-Voice Sample Parameters doc.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
