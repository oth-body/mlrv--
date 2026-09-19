#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/reverb_fx~.pd -- the reverb effect,
item 2 of the full-codebase gap analysis (see the Obsidian doc
"mlrv-pd -- Full Parity Gap Analysis"), corresponding to the original
`+REVERB.maxpat` + `yafr2.maxpat` (a Griesinger-style plate reverb by
Randy Jones, wrapped as a reusable sub-patch in the original).

Rather than hand-rolling a Schroeder/FDN reverb from scratch, this wraps
vanilla Pd's own bundled `[rev3~]` (found at /usr/lib/pd/extra/rev3~.pd,
confirmed loadable with NO extra -path flag needed -- same default-search
mechanism that already makes `expr~` work in master.pd without one).
Per its own help patch (rev3~-help.pd): "a more expensive, presumably
better reverberator than [rev2~] .. a bigger feedback delay network
matrix and an early reflections stage" -- a real, documented, production
FDN reverb, not a toy. 2 signal inlets (L/R), 4 signal outlets, plus 4
float control inlets (in THIS order, confirmed from rev3~-help.pd's own
connect list, not guessed): level (dB), liveness (0-100, "100 for
infinite reverb, 90 for longish, 80 for short" per its own help text),
crossover (Hz), damping (0-100, HF damping above crossover).

Bus architecture matches delay_fx~.pd exactly (see build_delay_fx.py's
docstring for the full design trail, including why the OUTPUT side is a
real `[outlet~]` rather than a second bus-based `[send~ fxin]` -- two
effects each with their own internal send~ fxin would collide, gotcha
#31): internally `[receive~ fxout]` (mixer's per-voice wet send, bus-
based -- multiple receivers on one send is safe, unlike multiple
senders) in, a real `[outlet~]` (wet signal) out. The mono aux bus is
duplicated into rev3~'s L/R inlets (no stereo signal exists anywhere
else in this mono port); all 4 of its outputs are summed and scaled down
(empirically tuned against a real impulse capture, not guessed -- see
run_reverb_fx_test.sh). The parent patch sums this abstraction's outlet~
with delay_fx~'s before the one real `[send~ fxin]`.

Defaults: level=90, liveness=85 (long-ish plate tail), crossover=3000Hz,
damping=20%. NOTE on "level": despite rev3~-help.pd's own text calling it
"dB, 0-100", it is NOT standard dBFS (0dB=unity) -- probe-verified
directly (a level-0 instance produced total silence for a sustained
sine input; level-100 produced full, substantial output). This is Pd's
own `[dbtorms]` convention used internally (confirmed by reading
rev3~.pd's source): 100 is the "reference" value near unity gain, 0 is
effectively off. Defaulting to 90, not 100, leaves a small headroom
margin, matching the spirit of master.pd's own 0.8 default gain.

Run from builders/: python3 build_reverb_fx.py
"""
import os
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

OUT = "/home/aandi/repos/mlrv--/.claude/worktrees/osc-control/mlrv-pd/abstractions/reverb_fx~.pd"
assert not os.path.exists(OUT), "reverb_fx~.pd exists -- refusing to double-build"

p = Patch(w=700, h=460)

usage = p.text(20, 20,
    "reverb_fx~.pd -- plate reverb effect (1:1 mlrv recreation \\, gap analysis item 2 \\, "
    "corresponds to +REVERB.maxpat/yafr2.maxpat). Wraps vanilla Pd's bundled [rev3~] "
    "(a real FDN reverb with early reflections \\, not hand-rolled). receive~ fxout in "
    "(mixer's per-voice wet send \\, bus-based) \\, real outlet~ out (wet signal -- the "
    "parent sums every effect's outlet~ before the one real send~ fxin). Control inlet: "
    "\\\"level <dB>\\\" \\, \\\"liveness <0-100>\\\" \\, \\\"crossover <hz>\\\" \\, "
    "\\\"damping <0-100>\\\" -- same names/ranges as rev3~'s own documented interface \\, "
    "passed straight through. NOTE: \\\"level\\\" is NOT standard dBFS despite rev3~-help.pd "
    "calling it dB -- 0 is near-silent \\, 100 is near-unity (Pd's own dbtorms convention \\, "
    "probe-verified before picking the level=90 default below).")

rx_in = p.obj(20, 100, "receive~ fxout")
ctl_in = p.obj(300, 100, "inlet")
r_ctl = p.obj(300, 140, "route level liveness crossover damping")

rev = p.obj(20, 220, "rev3~ 90 85 3000 20")
p.connect(rx_in, 0, rev, 0)
p.connect(rx_in, 0, rev, 1)
p.connect(r_ctl, 0, rev, 2)
p.connect(r_ctl, 1, rev, 3)
p.connect(r_ctl, 2, rev, 4)
p.connect(r_ctl, 3, rev, 5)
p.connect(ctl_in, 0, r_ctl, 0)

sum1 = p.obj(20, 280, "+~")
sum2 = p.obj(20, 320, "+~")
sum3 = p.obj(20, 360, "+~")
scale = p.obj(20, 400, "*~ 0.25")
wet_out = p.obj(300, 400, "outlet~")

p.connect(rev, 0, sum1, 0)
p.connect(rev, 1, sum1, 1)
p.connect(sum1, 0, sum2, 0)
p.connect(rev, 2, sum2, 1)
p.connect(sum2, 0, sum3, 0)
p.connect(rev, 3, sum3, 1)
p.connect(sum3, 0, scale, 0)
p.connect(scale, 0, wet_out, 0)

p.write(OUT)
print("wrote reverb_fx~.pd")
