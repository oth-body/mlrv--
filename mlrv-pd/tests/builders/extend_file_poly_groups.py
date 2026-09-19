#!/usr/bin/env python3
"""Extend file_poly.pd: `group <slot 0-7> <groupNum>` (1:1 mlrv recreation,
mute-group item, increment 1 of 2 -- storage only, no exclusivity behavior
yet, see extend_file_poly_group_exclusivity.py for increment 2).

Sourced from trentgill/mlrv's own docs ("each of the four (or six) groups
will allow only one sample to play at a time... triggering a different
sample in that same group whilst another is playing will cancel the
playback of the previously playing sample") and this repo's own ch.maxpat
(a 4-tab `group` selector, varname "group", default index 0) -- see
[[mlrv-pd -- 1:1 mlrv Recreation and Packaging]] in the Obsidian vault.

Design choice, deliberate and different from the Max default: group 0
means UNGROUPED here (no exclusivity), not "group 1" -- so slots nobody
has explicitly grouped never surprise-cancel each other. Groups 1-4 are
real mutually-exclusive groups. (The original defaults every channel
into group index 0 / displayed "1", which would make untouched slots
exclusive by default -- judged confusing for this port's purposes.)

New: `[table mlrv-fpgroup 8]` tracks each SLOT's assigned group (0 =
ungrouped, table inits 0 -- this IS the deliberate default above, no
loadbang-seeding needed). `route` gains `group` (new outlet 9); existing
outlets 0-8 (load/play/playv/stop/stopall/unload/query/gain/pitch)
untouched. Gated 0..7 like `unload` (out-of-range ignored, not clamped
onto a neighbor -- same philosophy, same route-based gate).

tabwrite's message is VALUE then INDEX (gotcha 13) -- unpack fires
right-to-left, so slot (1st atom) arrives LAST and must be the pack's
HOT inlet per gotcha 15; that makes pack emit "slot groupNum", the WRONG
order, fixed by a `msg $2 $1` reorder before the tabwrite (same pattern
this file already uses for mlrv-fplen loads).

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

OLD_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch;"
NEW_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch group;"
if NEW_ROUTE in body:
    sys.exit("already extended -- refusing to double-append")
assert body.count(OLD_ROUTE) == 1, "route line not found exactly once"

ROUTE_IDX = body.index(OLD_ROUTE)
assert ROUTE_IDX == 9, f"route index moved: {ROUTE_IDX}"
assert not any(c.startswith(f"#X connect {ROUTE_IDX} 9 ") for c in conns), \
    "route outlet 9 (old reject) already connected -- design assumption broken"
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

Y = 2500

T_FPGROUP = obj(700, Y, "table mlrv-fpgroup 8")
TW_FPGROUP = obj(700, Y + 60, "tabwrite mlrv-fpgroup")

# gate 0..7 (unload's exact pattern: reject out-of-range, don't clamp)
G_ROUTE = obj(20, Y, "route 0 1 2 3 4 5 6 7")
G_UNP = obj(20, Y - 50, "unpack f f")
connect(ROUTE_IDX, 9, G_UNP, 0)
G_MSG = [msg(60 + 80 * i, Y + 50, str(i)) for i in range(8)]
G_TFF = obj(60, Y + 100, "t f f")
G_PACK = obj(60, Y + 150, "pack f f")
G_SWAP = msg(60, Y + 200, "\\$2 \\$1")

# unpack: outlet1 (groupNum, 2nd atom) fires first -> cold-set pack inlet1;
# outlet0 (slot, 1st atom) fires last -> gate, then hot-trigger pack inlet0.
connect(G_UNP, 1, G_PACK, 1)
connect(G_UNP, 0, G_ROUTE, 0)
for i in range(8):
    connect(G_ROUTE, i, G_MSG[i], 0)
    connect(G_MSG[i], 0, G_PACK, 0)
connect(G_PACK, 0, G_SWAP, 0)
connect(G_SWAP, 0, TW_FPGROUP, 0)

text(20, Y + 250,
     "group <slot 0-7> <groupNum> (route outlet 9) -- 2026-09-18 \\, 1:1 mlrv recreation \\, "
     "mute-group item \\, increment 1 of 2 (storage only -- see CLAUDE.md's Packaging/1:1 "
     "sections and the Obsidian doc for the full design). mlrv-fpgroup tracks each slot's "
     "assigned group (0 = ungrouped \\, this port's own deliberate default \\, NOT the "
     "original's default-group-1 behavior -- see this script's own module docstring for "
     "why). Gated 0..7 like unload (out-of-range ignored \\, not clamped onto a neighbor). "
     "Exclusivity behavior (stopping a group-mate on trigger) and groupstop <groupNum> are "
     "increment 2 \\, not built yet -- this increment only stores assignments.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
