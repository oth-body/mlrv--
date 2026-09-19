#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/delay_fx~.pd -- the delay effect,
item 1 of the full-codebase gap analysis (see the Obsidian doc
"mlrv-pd -- Full Parity Gap Analysis"), corresponding to the original
`+DELAY.maxpat` (618 boxes, the largest patch in mlrv2/patchers/).

Scope for this increment: a single feedback delay line with smoothed
time and feedback controls -- the actual DSP core of the original patch.
NOT attempted here (documented, not hidden): the original's LPF-in-loop
tone control (seen on +AUXGRID's sibling delay, "LPF"/"FEEDBACK"/"TIME"
labels) and its LCD/multislider tap-tempo UI -- this abstraction is the
headless engine underneath, control messages only, matching this port's
approach everywhere else (mapper.pd/mlrv-gui.pd already provide the
"real GUI" layer that a `time`/`feedback` pair of engine messages can be
mapped to exactly like every other engine parameter in mapper_params.py).

Design references consulted before building (not guessed):
- Pd's own bundled `G03.delay.variable.pd` (3.audio.examples): the
  canonical variable-delay idiom used here -- `[pack f <ramp-ms>] ->
  [line~] -> [delread4~ name]`'s signal inlet for click-free time changes
  (4-point interpolation, smoother than plain `[delread~]`/`[vd~]`).
- That same example's own commentary: clip the signal INSIDE the feedback
  loop to avoid instabilities when feedback is pushed high, and a
  `[hip~ 5]` after the read to remove DC buildup in the loop. Both are in
  place here.
- Original mlrv2 comments (`+DELAY.maxpat`: "feedback amount", "delay
  time"; `+AUXGRID.maxpat`: "TIME"/"FEEDBACK"/"SLIDE TIME") confirm the
  two controls built here (`time`, `feedback`) are the real core params,
  and that a smoothed ("slide") time change (not an instant jump) matches
  the original's own intent, not just a Pd-side nicety.

Bus architecture, INPUT side (matches this codebase's ALREADY-established,
ALREADY-TESTED aux-send convention -- see mixer.pd's own doc comment and
mlrv_core.py's original "fxin stub" comment, both of which independently
describe "between mixer fxout and master fxin" as the intended effect
insertion point): `[receive~ fxout]` (mixer.pd's per-voice wet/send sum)
in. Multiple `[receive~ fxout]` objects (one per effect) reading the same
send is completely safe -- a bus can have many listeners, unlike senders.

Bus architecture, OUTPUT side: a real `[outlet~]`, NOT a `[send~ fxin]`
-- this changed from an earlier version of this builder after adding a
SECOND effect (`reverb_fx~.pd`) revealed why a bus-based *output* doesn't
generalize: two effects each with their own internal `[send~ fxin]` would
collide exactly like gotcha #31 describes (whichever is instantiated
first in the parent silently wins, the other's return vanishes with only
a `multiply defined` warning as a clue). The parent patch (`mlrv_core.py`/
`build_mlrv_gui.py`) now sums every effect's real `outlet~` explicitly
with `[+~]` before the ONE real `[send~ fxin]` that actually exists
anywhere -- ordinary Pd signal wiring, not a second bus, so it can't
collide by construction. `master.pd`'s own internal `[send~ fxout]`
(Turn 13, self-test only, see gotcha #31) still doesn't need touching --
it only ever collided with `[send~ fxout]` senders, and this abstraction
was never one of those (INPUT side only reads fxout, never sends it).

Interface: no creation arg (fixed 2000ms max buffer -- generous for a
sample-slicing instrument, not a design parameter worth exposing yet).
Control inlet: `time <ms>` (clipped 1-2000, smoothed over 50ms),
`feedback <0-1>` (clipped 0-0.95 to avoid runaway, smoothed over 20ms).
Signal: no inlet~ (input arrives only via the internal `[receive~ fxout]`
bus tap), one real `outlet~` (wet signal, for the parent to sum with
other effects before the shared `[send~ fxin]`).

Run from builders/: python3 build_delay_fx.py
"""
import os
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

OUT = "/home/aandi/repos/mlrv--/.claude/worktrees/osc-control/mlrv-pd/abstractions/delay_fx~.pd"
assert not os.path.exists(OUT), "delay_fx~.pd exists -- refusing to double-build"

p = Patch(w=700, h=520)

usage = p.text(20, 20,
    "delay_fx~.pd -- feedback delay effect (1:1 mlrv recreation \\, gap analysis item 1 \\, "
    "corresponds to +DELAY.maxpat). receive~ fxout in (mixer's per-voice wet send \\, bus-"
    "based) \\, real outlet~ out (wet signal -- the parent sums every effect's outlet~ before "
    "the one real send~ fxin \\, see this builder script's docstring for why a second bus-"
    "based send~ fxin doesn't generalize to multiple effects). Control inlet: "
    "\\\"time <ms>\\\" (1-2000 \\, smoothed 50ms slide) \\, \\\"feedback <0-1>\\\" "
    "(clipped 0-0.95 \\, smoothed 20ms).")

rx_in = p.obj(20, 100, "receive~ fxout")
ctl_in = p.obj(300, 100, "inlet")
r_ctl = p.obj(300, 140, "route time feedback")

# --- time control: clip -> pack (target, ramp-ms) -> line~ -> delread4~ signal inlet ---
t_clip = p.obj(300, 180, "clip 1 2000")
t_pack = p.obj(300, 220, "pack f 50")
t_line = p.obj(300, 260, "line~")

# --- feedback control: clip -> pack (target, ramp-ms) -> line~ (smoothed gain signal) ---
# NOTE: line~'s optional creation arg sets an initial VALUE (instant jump at
# load), not a default ramp time for later bare floats -- a bare float into
# line~'s left inlet with no paired ramp-time is an instant jump (click
# risk). Use the same pack-then-line~ idiom as the time control above.
f_clip = p.obj(460, 180, "clip 0 0.95")
f_pack = p.obj(460, 220, "pack f 20")
f_line = p.obj(460, 260, "line~")

# --- signal chain: dry-in + feedback -> safety clip -> delwrite~; delread4~ time-controlled ---
sum_in = p.obj(20, 260, "+~")
clip_loop = p.obj(20, 300, "clip~ -0.98 0.98")
dw = p.obj(20, 340, "delwrite~ mlrv-delaybuf 2000")
dr = p.obj(300, 300, "delread4~ mlrv-delaybuf")
dc_block = p.obj(300, 340, "hip~ 5")
fb_mul = p.obj(460, 380, "*~")
wet_out = p.obj(300, 420, "outlet~")

p.connect(rx_in, 0, sum_in, 0)
p.connect(ctl_in, 0, r_ctl, 0)
p.connect(r_ctl, 0, t_clip, 0)
p.connect(t_clip, 0, t_pack, 0)
p.connect(t_pack, 0, t_line, 0)
p.connect(t_line, 0, dr, 0)
p.connect(r_ctl, 1, f_clip, 0)
p.connect(f_clip, 0, f_pack, 0)
p.connect(f_pack, 0, f_line, 0)
p.connect(dr, 0, dc_block, 0)
p.connect(dc_block, 0, wet_out, 0)
p.connect(dc_block, 0, fb_mul, 0)
p.connect(f_line, 0, fb_mul, 1)
p.connect(fb_mul, 0, clip_loop, 0)
p.connect(clip_loop, 0, sum_in, 1)
p.connect(sum_in, 0, dw, 0)

p.write(OUT)
print("wrote delay_fx~.pd")
