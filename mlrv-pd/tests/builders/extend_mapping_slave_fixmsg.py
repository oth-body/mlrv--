#!/usr/bin/env python3
"""Fix mapping.pd held-play rebuild message (slave wiring follow-up).

Root cause, found by comparing real output against hand-derived values
rather than inspection: the pending store is a 5-inlet `[pack f f f f f]`
whose inlet 0 is bang-to-reemit only, so the stored atoms sit one position
to the right of the 4-inlet pack the template was copied from. The copied
`play $2 $4 $1 $3` (correct for pack20's [start slot end rate] at inlets
0-3) reads the shifted layout as play slot=0 rate=4410 start=0 end=0.
Correct template for [0 start slot end rate] (inlet0 always 0) is
`play $3 $5 $2 $4` = play slot rate start end.

Refuses to run twice.
"""

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/mapping.pd"

WRONG = "#X msg 220 1960 play \\$2 \\$4 \\$1 \\$3;"
RIGHT = "#X msg 220 1960 play \\$3 \\$5 \\$2 \\$4;"

with open(PATH) as f:
    lines = f.read().splitlines()

if RIGHT in lines:
    import sys
    sys.exit("already fixed -- refusing to double-apply")
assert lines.count(WRONG) == 1, "wrong template not found exactly once"
lines[lines.index(WRONG)] = RIGHT

with open(PATH, "w") as f:
    f.write("\n".join(lines) + "\n")
print("fixed held-play rebuild template")
