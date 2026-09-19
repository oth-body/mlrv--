#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_glow.pd.

Deterministic toy test (metro off via [glow 1000000]):
  paint (2,3) -> immediate 15, then decay 13/10 across ticks;
  ball spawns (3,3) and shows once decayed;
  5x tilt +x -> comet visibly travels (4 3 13);
  shake-tilt -> next tick emits zero-levels (2 3 0).
Run from this directory:  python3 build_test_glow.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=400)

GLOW = p.obj(60, 60, "glow 1000000")
GLED = p.obj(60, 120, "print gled")
p.connect(GLOW, 0, GLED, 0)

p.timeline(60, 200, [
    (100, "tick", GLOW, 0),
    (200, "list 2 3 1", GLOW, 0),
    (300, "tick", GLOW, 0),
    (400, "tick", GLOW, 0),
    (500, "tilt 200 127 127", GLOW, 0),
    (520, "tilt 200 127 127", GLOW, 0),
    (540, "tilt 200 127 127", GLOW, 0),
    (560, "tilt 200 127 127", GLOW, 0),
    (580, "tilt 200 127 127", GLOW, 0),
    (600, "tick", GLOW, 0),
    (700, "tick", GLOW, 0),
    (800, "tilt 200 200 200", GLOW, 0),
    (900, "tick", GLOW, 0),
])

p.write("../test_glow.pd")
print("wrote test_glow.pd:", len(p.objs), "objects,", len(p.conns), "connections")
