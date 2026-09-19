#!/usr/bin/env python3
"""Fix clock.pd tempo path: refresh the quantize factor before recomputing
the metro interval (1:1 mlrv recreation, slave-wiring follow-up).

Root cause, probe-verified in /tmp (mult_probe.pd): `[ * ]`'s cold inlet
inits to 0, and NOTHING on the tempo path ever sets it -- only quantize
receipts reach it (via `[t b f]`). At load this is masked (the metro keeps
its 500ms creation-arg interval; an interval-0 write pre-first-tick is
ignored -- probed), so the default-tempo regression passes. But the first
real `tempo <bpm>` receipt computes msPerBeat x 0 = 0 and writes interval 0
to a RUNNING metro, which floods (~360 ticks/sec observed, vs the 500ms
grid). The quantize path was always correct (it sets the factor first,
then re-emits tempo) -- the tempo path just never did the first half.

Fix (2 objects, purely additive on the tempo path; load/default behavior
unchanged): route-tempo-outlet -> `[t f b]` -> outlet1 (bang, fires first)
re-emits the stored quantize factor into `[t b f]` (which sets the mult's
cold inlet BEFORE its bang re-emits tempo -- the same right-to-left order
the quantize path already relies on); outlet0 (the tempo float, fires
second) sets `[float 120]` as before.

Refuses to run twice.
"""

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/abstractions/clock.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

assert lines[0].startswith("#N canvas"), "unexpected header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert len(body) + len(conns) == len(lines) - 1, "unexpected line types present"

assert not any("t f b" in l for l in lines), "already extended -- refusing to double-append"
OLD = "#X connect 2 0 3 0;"
assert conns.count(OLD) == 1, "route-tempo->float120 connect not found exactly once"
conns.remove(OLD)

def idx():
    return len(body) + len(objs) - 1

objs = []
objs.append("#X obj 380 130 t f b;")
TFB = idx()
objs.append("#X text 380 170 tempo path refreshes the quantize factor first (2026-09-18 \\, slave-wiring follow-up): mult cold-init is 0 and only quantize receipts ever set it \\, so a bare tempo receipt used to compute interval 0 and flood a running metro -- probed in /tmp/mult_probe.pd. t f b bangs float-1 (re-emit factor into t b f) before the tempo float sets float-120.;")

newconns = [
    f"#X connect 2 0 {TFB} 0;",
    f"#X connect {TFB} 1 5 0;",
    f"#X connect {TFB} 0 3 0;",
]

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended clock.pd: 2 objects, {len(newconns)} new connects")
