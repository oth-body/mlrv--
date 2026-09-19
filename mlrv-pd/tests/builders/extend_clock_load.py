#!/usr/bin/env python3
"""Fix clock.pd load-time metro interval (slave-wiring follow-up).

Root cause, probe-verified in /tmp (mult_probe.pd + clock_flood.pd):
`[ * ]`'s cold inlet inits to 0 and nothing at load ever sets it, so the
load-time recompute writes interval 500 x 0 = 0 to the metro. Pd's metro
adopts a new interval when scheduling its NEXT tick: the pending
500ms tick (scheduled by loadbang just before) still fires on time --
which is why the default-tempo regression always passed and the release
timing looked perfect -- but every tick after that reschedules with
interval 0, i.e. immediately: the beat outlet floods (~750 ticks/sec
observed standalone) from the second tick on. Nothing ever observed
outlet1 before the slave-wiring test, so nobody noticed.

Fix (one connect swap, load path only): loadbang fans into `[float 1]`
(the quantize store) instead of directly into `[float 120]`. Re-emitting
the factor through the existing `[t b f]` sets the mult's cold inlet to 1
FIRST and then re-emits tempo through `[float 120]` SECOND (the same
right-to-left order the quantize path already relies on), so the
load-time compute is 500 x 1 = 500 -- a correct, nonzero interval from
the first tick. The removed direct loadbang->float120 recompute is
subsumed by it (same value, same tick).

Refuses to run twice.
"""

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/abstractions/clock.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

OLD = "#X connect 9 0 3 0;"
NEW = "#X connect 9 0 5 0;"
if NEW in lines:
    import sys
    sys.exit("already fixed -- refusing to double-apply")
assert lines.count(OLD) == 1, "loadbang->float120 connect not found exactly once"
lines[lines.index(OLD)] = NEW

with open(PATH, "w") as f:
    f.write("\n".join(lines) + "\n")
print("fixed clock.pd load-time interval (loadbang now seeds quantize factor first)")
