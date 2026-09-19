#!/usr/bin/env python3
"""Extend file_poly.pd: automatic mute-group exclusivity on every play/playv
trigger, plus `groupstop <groupNum 1-4>`. Increment 2 of 2 for the
mute-group item (1:1 mlrv recreation track) -- see
extend_file_poly_groups.py (increment 1, group assignment storage) and
[[mlrv-pd -- 1:1 mlrv Recreation and Packaging]] for the full design.

Sourced from trentgill/mlrv's own docs: "triggering a different sample in
that same group whilst another is playing will cancel the playback of
the previously playing sample... each group has a 'group stop' button."

Mechanism, probe-verified before writing into this file (see
/tmp/group_probe/expr_multi_probe3.pd): a multi-inlet [expr] evaluates
correctly as long as every COLD inlet ($i2, $i3, ...) is loaded before
the HOT inlet ($i1, always the first $iN referenced in the expr string)
fires -- confirmed with a hand-computed case (result 1, matching
(3 != $i1=7) && ($i2=5 == $i3=5) && ($i3=5 != 0)).

Taps the EXISTING pack(voice,slot,rate,start,end) used by both the play
and playv dispatch branches -- purely additive, does not touch either
branch's own already-tested wiring. [unpack f f] on that 5-tuple takes
only the first two atoms (probe-verified: unpack tolerates a longer
list, ignoring trailing atoms, no error) and relies on the SAME
right-to-left firing already used throughout this file: slot (2nd
unpack outlet by position, fires FIRST) drives the group lookup and the
four voices' tracked-group tabreads; voice (1st outlet, fires LAST)
is the trigger for all four branches' comparisons and the tracker
write, by which point every value the comparisons need is already
sitting on a cold inlet.

group 0 = ungrouped by this port's own deliberate convention (increment
1's docstring) -- explicitly excluded from ever causing a stop via the
"$i3 != 0" / "$i1 != 0" clauses below, not merely relying on a
coincidental table-default value never matching.

New: `[table mlrv-fpvgroup 5]` (5 cells, not 4 -- voice numbers are
1-4, used directly as the index, index 0 permanently unused; avoids an
extra "-1" arithmetic object on every read/write for one wasted float).

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

OLD_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch group;"
NEW_ROUTE = "#X obj 20 130 route load play playv stop stopall unload query gain pitch group groupstop;"
if NEW_ROUTE in body:
    sys.exit("already extended -- refusing to double-append")
assert body.count(OLD_ROUTE) == 1, "route line not found exactly once (run increment 1 first?)"

ROUTE_IDX = body.index(OLD_ROUTE)
assert ROUTE_IDX == 9, f"route index moved: {ROUTE_IDX}"
assert not any(c.startswith(f"#X connect {ROUTE_IDX} 10 ") for c in conns), \
    "route outlet 10 (old reject) already connected -- design assumption broken"

PACK_TXT = "#X obj 340 380 pack f f f f f;"
assert body.count(PACK_TXT) == 1, "shared voice/slot/rate/start/end pack not found exactly once"
PACK_IDX = body.index(PACK_TXT)
assert PACK_IDX == 25, f"pack index moved: {PACK_IDX}"

SV_TXT = [
    "#X obj 460 760 sample_voice~ mlrv-sample-0;",
    "#X obj 460 820 sample_voice~ mlrv-sample-1;",
    "#X obj 460 880 sample_voice~ mlrv-sample-2;",
    "#X obj 460 940 sample_voice~ mlrv-sample-3;",
]
SV_IDX = []
for t in SV_TXT:
    assert body.count(t) == 1, f"{t} not found exactly once"
    SV_IDX.append(body.index(t))
assert SV_IDX == [75, 76, 77, 78], f"sample_voice~ indices moved: {SV_IDX}"

GROUP_TABLE_TXT = "#X obj 700 2500 table mlrv-fpgroup 8;"
assert body.count(GROUP_TABLE_TXT) == 1, "mlrv-fpgroup table not found -- run increment 1 first"

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

Y = 3000

T_FPVGROUP = obj(700, Y, "table mlrv-fpvgroup 5")
TW_FPVGROUP = obj(700, Y + 60, "tabwrite mlrv-fpvgroup")

# --- trigger-exclusivity: taps pack(25)'s output, purely additive ---
EX_UNP = obj(20, Y, "unpack f f")
connect(PACK_IDX, 0, EX_UNP, 0)

EX_SLOT_TB = obj(20, Y + 50, "t b")     # slot arrival -> bang, drives the 4 tracked-group reads
EX_GLOOKUP = obj(160, Y + 50, "tabread mlrv-fpgroup")
connect(EX_UNP, 1, EX_SLOT_TB, 0)
connect(EX_UNP, 1, EX_GLOOKUP, 0)

EX_VMSG = [msg(20 + 60 * i, Y + 100, str(i + 1)) for i in range(4)]
EX_VTAB = [obj(20 + 60 * i, Y + 140, "tabread mlrv-fpvgroup") for i in range(4)]
for i in range(4):
    connect(EX_SLOT_TB, 0, EX_VMSG[i], 0)
    connect(EX_VMSG[i], 0, EX_VTAB[i], 0)

EX_EXPR = [
    obj(20 + 150 * i, Y + 200,
        f"expr ({i + 1} != $i1) && ($i2 == $i3) && ($i3 != 0)")
    for i in range(4)
]
EX_SEL = [obj(20 + 150 * i, Y + 240, "select 1") for i in range(4)]
for i in range(4):
    connect(EX_UNP, 0, EX_EXPR[i], 0)         # voice (fires last) -> $i1, HOT
    connect(EX_VTAB[i], 0, EX_EXPR[i], 1)     # this voice's tracked group -> $i2, cold
    connect(EX_GLOOKUP, 0, EX_EXPR[i], 2)     # triggering slot's group -> $i3, cold
    connect(EX_EXPR[i], 0, EX_SEL[i], 0)
    connect(EX_SEL[i], 0, SV_IDX[i], 0)       # bang = stop, sample_voice~'s own interface

# --- tracker write: mlrv-fpvgroup[voice] = G (this voice now sounds group G) ---
EX_WPACK = obj(700, Y + 140, "pack f f")
EX_WSWAP = msg(700, Y + 190, "\\$2 \\$1")
connect(EX_GLOOKUP, 0, EX_WPACK, 1)  # G, already available when slot fired -> cold
connect(EX_UNP, 0, EX_WPACK, 0)      # voice, fires last -> hot, triggers emission "voice G"
connect(EX_WPACK, 0, EX_WSWAP, 0)    # reorder to "G voice" (tabwrite is value-then-index)
connect(EX_WSWAP, 0, TW_FPVGROUP, 0)

# --- groupstop <groupNum 1-4> (route outlet 10) ---
# t b f: outlet0 = bang, outlet1 = float (type letters in written order =
# outlet order); BUT outlets still fire right-to-left regardless of type
# (gotcha #4, probe-reconfirmed here after an initial wiring bug caught
# this exact mismatch): outlet1 (float=groupNum) fires FIRST, outlet0
# (bang) fires LAST. So groupNum must be the COLD value and the
# bang-triggered tracked-group tabread must be the HOT/triggering one --
# the reverse of this section's first (buggy) draft.
GS_TBF = obj(1000, Y, "t b f")
connect(ROUTE_IDX, 10, GS_TBF, 0)
GS_VMSG = [msg(1000 + 60 * i, Y + 50, str(i + 1)) for i in range(4)]
GS_VTAB = [obj(1000 + 60 * i, Y + 90, "tabread mlrv-fpvgroup") for i in range(4)]
for i in range(4):
    connect(GS_TBF, 0, GS_VMSG[i], 0)   # bang, fires last -> trigger the read
    connect(GS_VMSG[i], 0, GS_VTAB[i], 0)

GS_EXPR = [obj(1000 + 150 * i, Y + 140, "expr ($i1 == $i2) && ($i2 != 0)") for i in range(4)]
GS_SEL = [obj(1000 + 150 * i, Y + 180, "select 1") for i in range(4)]
for i in range(4):
    connect(GS_VTAB[i], 0, GS_EXPR[i], 0)  # this voice's tracked group, fires last -> $i1, HOT
    connect(GS_TBF, 1, GS_EXPR[i], 1)      # groupNum, fires first -> $i2, cold
    connect(GS_EXPR[i], 0, GS_SEL[i], 0)
    connect(GS_SEL[i], 0, SV_IDX[i], 0)

text(20, Y + 300,
     "trigger-exclusivity + groupstop (route outlets: group=9 from increment 1 \\, "
     "groupstop=10 here) -- 2026-09-18 \\, 1:1 mlrv recreation \\, mute-group item \\, "
     "increment 2 of 2. Taps the EXISTING pack(voice \\, slot \\, rate \\, start \\, end) "
     "used by both play and playv dispatch -- purely additive \\, neither branch's own "
     "wiring was touched. On every trigger: looks up the target slot's group \\, stops any "
     "OTHER voice (not itself) whose currently-tracked group matches (skipping group 0 = "
     "ungrouped entirely \\, never causes a stop) \\, then records this voice's new group. "
     "groupstop works the same way minus the self-exclusion check. Multi-inlet [expr] "
     "ordering (cold inlets loaded before the hot inlet fires) was probe-verified in "
     "isolation first \\, not assumed -- see this script's own module docstring.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
