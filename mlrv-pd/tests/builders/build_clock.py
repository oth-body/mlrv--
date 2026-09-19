#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/clock.pd -- tempo/quantize/slave
subsystem, item 2 of the 1:1 mlrv recreation scope (see the Obsidian
"mlrv-pd -- 1:1 mlrv Recreation and Packaging" doc and CLAUDE.md).

trentgill/mlrv's own time.maxpat builds this on Max's [transport] object
plus symbolic time syntax (4n/16n/32n) -- Pd has no equivalent, so this
is a from-scratch subsystem, not a port of an existing Pd mechanism.
Scope: internal tempo/quantize only (no MIDI clock, no audio-sync, no
tilt-tempo -- all present in the original but out of scope here, no
MIDI/audio-sync hardware or need exists in this Pd port).

Interface: `tempo <bpm>` (default 120), `quantize <beats>` (default 1,
the grid size in beats a trigger gets held to), a bare `bang` (a trigger
to be quantize-gated -- held until the next grid boundary, then released
as a bang on outlet 0). Outlet 1 taps the raw beat-pulse metro directly,
for future use (e.g. LED sync) -- nearly free to expose, not asked for
by name in mlrv's docs but a natural byproduct of the metro already
needed internally.

Mechanism, probe-verified in isolation before being written here (see
/tmp/time_probe/quantize_gate_probe2.pd, 2026-09-18): tempo=120bpm +
quantize=1 beat -> 500ms metro grid; a trigger arriving at 220ms after
metro start was released at exactly 500ms (280ms later), confirmed via
Pd's own [timer], not just message-arrival order. The gate itself is the
"store silently, bang-to-read, sel 1, reset" idiom already used
throughout this port (mixer.pd's query, sample_voice~.pd's gain) -- a
[float 0] holds "pending" (0/1), metro's tick bangs it to re-emit, [sel
1] catches a real pending trigger and immediately resets the store.

The [t b f] on the quantize-recompute path was wired with the SAME
type-vs-firing-order care as gotcha #24 (mixed-type outlets: type order
matches written order, but firing order is still right-to-left
regardless of type) -- outlet1 (float, fires first) feeds the
multiply's cold inlet before outlet0 (bang, fires last) re-triggers the
bpm store's re-emission, so the interval recompute always uses the
freshly-set quantize value, never a stale one.

Deliberately NOT wired into file_poly.pd/mapping.pd/sample_voice~.pd in
this task -- a sibling task owns those files concurrently. The
integration point for a future `slave` feature: send a channel's
trigger bang into THIS abstraction's inlet instead of directly to
file_poly.pd's play/playv dispatch; the released bang on outlet 0 is
what should actually trigger playback. See the Obsidian doc for the
full writeup of what that wiring would need.

Run from builders/: python3 build_clock.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=600, h=550)

inlet = p.obj(20, 20, "inlet")
usage = p.text(120, 20,
    "tempo/quantize/slave clock (1:1 mlrv recreation item 2). inlet accepts "
    "\\\"tempo <bpm>\\\" (default 120) \\, \\\"quantize <beats>\\\" (default 1) \\, "
    "or a bare bang (a trigger to be held until the next quantize-grid boundary\\, "
    "then released on outlet 0). outlet 1 taps the raw beat-pulse metro directly.")

route = p.obj(20, 80, "route tempo quantize")
p.connect(inlet, 0, route, 0)

bpm = p.obj(20, 130, "float 120")
p.connect(route, 0, bpm, 0)  # tempo match -> hot inlet: store + emit

msperbeat = p.obj(20, 170, "expr 60000. / $i1")
p.connect(bpm, 0, msperbeat, 0)

qbeats = p.obj(200, 130, "float 1")
p.connect(route, 1, qbeats, 0)  # quantize match -> hot inlet: store + emit

recompute = p.obj(200, 170, "t b f")
p.connect(qbeats, 0, recompute, 0)

mult = p.obj(20, 210, "*")
p.connect(msperbeat, 0, mult, 0)
p.connect(recompute, 1, mult, 1)   # float (fires first) -> cold inlet
p.connect(recompute, 0, bpm, 0)    # bang (fires last) -> re-trigger bpm's re-emission

metro = p.obj(20, 250, "metro 500")
p.connect(mult, 0, metro, 1)  # update interval, don't restart

lb = p.obj(300, 20, "loadbang")
m_start = p.msg(300, 60, "1")
p.connect(lb, 0, m_start, 0)
p.connect(m_start, 0, metro, 0)
p.connect(lb, 0, bpm, 0)  # kick the initial computation with a bang (re-emits default 120)

# --- quantize gate ---
m_setpending = p.msg(20, 300, "1")
p.connect(route, 2, m_setpending, 0)  # reject outlet = bare bang trigger

pending = p.obj(20, 340, "float 0")
p.connect(m_setpending, 0, pending, 1)  # cold-set pending=1, no emit
p.connect(metro, 0, pending, 0)         # every tick: bang re-emits current pending value

sel = p.obj(20, 380, "sel 1")
p.connect(pending, 0, sel, 0)

m_resetpending = p.msg(120, 380, "0")
p.connect(sel, 0, m_resetpending, 0)
p.connect(m_resetpending, 0, pending, 1)  # reset for next cycle, cold (no emit)

out_released = p.obj(20, 430, "outlet")
p.connect(sel, 0, out_released, 0)

out_pulse = p.obj(200, 430, "outlet")
p.connect(metro, 0, out_pulse, 0)

verified = p.text(20, 470,
    "verified 2026-09-18 (1:1 mlrv recreation \\, item 2): metro-interval math and the "
    "quantize-gate mechanism (store-silently / bang-to-read / sel-and-reset) were probe-"
    "verified in isolation first against Pd's own [timer] \\, not just message-arrival "
    "order -- 120bpm + quantize=1 beat = 500ms grid \\; a trigger fired 220ms after metro "
    "start was released exactly 280ms later (at the 500ms boundary) \\, matching this session's "
    "established discipline of verifying real behavior before relying on a mechanism. "
    "See tests/run_clock_test.sh for the real regression test. NOT wired into file_poly.pd / "
    "mapping.pd / sample_voice~.pd yet -- see the Obsidian 1:1 recreation doc for the "
    "documented integration point for a future slave feature.")

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/clock-subsystem/mlrv-pd/abstractions/clock.pd")
print("wrote clock.pd")
