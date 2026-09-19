#!/usr/bin/env python3
"""Extend mapping.pd: `slave <slot 0-7> <0|1>` + `tempo`/`quantize` forwarding
(1:1 mlrv recreation, item 2 -- slave wiring, the documented integration
point from CLAUDE.md: a slaved channel's trigger goes through clock.pd
instead of straight to play dispatch).

Design (all mechanisms probe-verified in /tmp before writing, per standing
discipline -- see this task's probe patches gate_probe/spigot_probe/
pack_probe):
- `[table mlrv-mslave 8]` tracks each slot's tempo-slave flag (0 = immediate,
  the default via table zero-init, same rationale as file_poly's fpgroup).
  `slave <slot> <0|1>` stores via the proven gated route-0..7 + value-first
  tabwrite idiom (mirrors extend_file_poly_groups.py exactly).
- `tempo <bpm>` / `quantize <beats>` are re-tagged (`route` strips the
  selector, so re-prepend via msg before forwarding) into a contained
  `[clock]` instance (no creation args, fully self-contained).
- Trigger gating taps pack (start slot end rate) output: `[t l l]` splits it.
  Outlet 1 (fires first) reads the slot's flag via tabread and pre-sets a
  spigot pair (immediate vs held) -- outlet 0 (fires second) then delivers
  the message through exactly one of them. Depth-first trigger ordering
  (gotcha 25's own fix pattern) makes the control-before-data order airtight.
  `[gate]` does NOT exist in vanilla Pd 0.56.5 (probe: "couldn't create") --
  the spigot pair is its replacement, and this is new CLAUDE.md gotcha #27.
- Held triggers cold-store into a 5-inlet `[pack f f f f f]` (4 cold inlets +
  bang-to-reemit hot inlet -- probed: no premature emit, bang re-emits the
  full stored list) and fire on clock.pd's release bang, rebuilt as
  `play <slot> <rate> <start> <end>` through a duplicate play msg.
  Last-write-wins if retriggered while held (documented, not hidden).
- LED feedback stays immediate (press ack) even for slaved slots -- only the
  play message is held. New outlet 2 (x=300, highest x per gotcha 10)
  exposes clock.pd's raw beat pulse for future LED sync; existing outlets
  0/1 keep their indices.
- Known limits (MVP, documented not hidden): stopall does not cancel a held
  trigger; direct file_poly.pd play messages are never gated (grid path
  only); no grid gesture sets slave/tempo/quantize yet (message interface
  only, same reachability-gap convention as every other 1:1 item).

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
assert len(body) == 39, f"body moved: {len(body)}"
assert len(conns) == 52, f"connects moved: {len(conns)}"

assert body[3] == "#X obj 20 80 route list;", "route-list index moved"
assert body[21] == "#X msg 20 880 play \\$2 \\$4 \\$1 \\$3;", "play msg moved"
assert not any("mlrv-mslave" in l for l in lines), "already extended -- refusing to double-append"
assert not any(c.startswith("#X connect 3 1 ") for c in conns), \
    "route-list reject already connected -- design assumption broken"
OLD_PLAY = "#X connect 20 0 21 0;"
assert conns.count(OLD_PLAY) == 1, "pack->play connect not found exactly once"
conns.remove(OLD_PLAY)

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

Y = 1000

T_MSLAVE = obj(700, Y, "table mlrv-mslave 8")
TW_MSLAVE = obj(700, Y + 180, "tabwrite mlrv-mslave")

CTL_ROUTE = obj(20, Y, "route slave tempo quantize")
S_UNP = obj(20, Y + 60, "unpack f f")
S_GATE = obj(20, Y + 120, "route 0 1 2 3 4 5 6 7")
S_MSG = [msg(60 + 80 * i, Y + 180, str(i)) for i in range(8)]
S_PACK = obj(60, Y + 240, "pack f f")
S_SWAP = msg(60, Y + 300, "\\$2 \\$1")
T_MSG = msg(420, Y + 60, "tempo \\$1")
Q_MSG = msg(540, Y + 60, "quantize \\$1")
CLOCK = obj(420, Y + 120, "clock")

connect(3, 1, CTL_ROUTE, 0)
connect(CTL_ROUTE, 0, S_UNP, 0)
connect(S_UNP, 1, S_PACK, 1)
connect(S_UNP, 0, S_GATE, 0)
for i in range(8):
    connect(S_GATE, i, S_MSG[i], 0)
    connect(S_MSG[i], 0, S_PACK, 0)
connect(S_PACK, 0, S_SWAP, 0)
connect(S_SWAP, 0, TW_MSLAVE, 0)
connect(CTL_ROUTE, 1, T_MSG, 0)
connect(T_MSG, 0, CLOCK, 0)
connect(CTL_ROUTE, 2, Q_MSG, 0)
connect(Q_MSG, 0, CLOCK, 0)

T_SPLIT = obj(20, Y + 360, "t l l")
connect(20, 0, T_SPLIT, 0)
F_UNP = obj(120, Y + 420, "unpack f f f f")
F_TAB = obj(120, Y + 480, "tabread mlrv-mslave")
F_ROUTE = obj(120, Y + 540, "route 0 1")
N_IMM = obj(120, Y + 600, "t b b")
N_HELD = obj(320, Y + 600, "t b b")
M_IMM_OPEN = msg(60, Y + 660, "1")
M_HELD_SHUT = msg(140, Y + 660, "0")
M_IMM_SHUT = msg(260, Y + 660, "0")
M_HELD_OPEN = msg(340, Y + 660, "1")
SP_IMM = obj(20, Y + 720, "spigot")
SP_HELD = obj(220, Y + 720, "spigot")
T_ORDER = obj(20, Y + 780, "t l l")
connect(T_SPLIT, 1, F_UNP, 0)
connect(F_UNP, 1, F_TAB, 0)
connect(F_TAB, 0, F_ROUTE, 0)
connect(F_ROUTE, 0, N_IMM, 0)
connect(F_ROUTE, 1, N_HELD, 0)
connect(N_IMM, 1, M_IMM_OPEN, 0)
connect(M_IMM_OPEN, 0, SP_IMM, 1)
connect(N_IMM, 0, M_HELD_SHUT, 0)
connect(M_HELD_SHUT, 0, SP_HELD, 1)
connect(N_HELD, 1, M_IMM_SHUT, 0)
connect(M_IMM_SHUT, 0, SP_IMM, 1)
connect(N_HELD, 0, M_HELD_OPEN, 0)
connect(M_HELD_OPEN, 0, SP_HELD, 1)
connect(T_SPLIT, 0, T_ORDER, 0)
connect(T_ORDER, 1, SP_IMM, 0)
connect(T_ORDER, 0, SP_HELD, 0)
connect(SP_IMM, 0, 21, 0)

H_SPLIT = obj(220, Y + 780, "t l b")
H_UNP = obj(220, Y + 840, "unpack f f f f")
H_PACK = obj(220, Y + 900, "pack f f f f f")
H_MSG = msg(220, Y + 960, "play \\$2 \\$4 \\$1 \\$3")
connect(SP_HELD, 0, H_SPLIT, 0)
connect(H_SPLIT, 1, CLOCK, 0)
connect(H_SPLIT, 0, H_UNP, 0)
connect(H_UNP, 0, H_PACK, 1)
connect(H_UNP, 1, H_PACK, 2)
connect(H_UNP, 2, H_PACK, 3)
connect(H_UNP, 3, H_PACK, 4)
connect(CLOCK, 0, H_PACK, 0)
connect(H_PACK, 0, H_MSG, 0)
connect(H_MSG, 0, 37, 0)

BEAT = obj(300, Y + 1020, "outlet")
connect(CLOCK, 1, BEAT, 0)

text(20, Y + 1080,
     "slave / tempo / quantize (route-list reject -- 2026-09-18 \\, 1:1 mlrv recreation item 2 "
     "slave wiring). table mlrv-mslave 8 tracks each slot's tempo-slave flag (0 = immediate \\, "
     "default). trigger path: pack output splits through t l l -- outlet 1 (first) reads the "
     "slot flag and pre-sets the spigot pair \\, outlet 0 (second) delivers through exactly one "
     "of them. held triggers cold-store in the 5-inlet pack and fire on clock.pd's release bang "
     "(last-write-wins). LED stays immediate. outlet 2 = clock beat pulse. limits: stopall does "
     "not cancel a held trigger \\, direct file_poly play messages are never gated \\, no grid "
     "gesture sets slave/tempo/quantize yet.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
