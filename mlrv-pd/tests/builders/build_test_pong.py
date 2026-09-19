#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_pong.pd.

Deterministic logic test: metro effectively off ([pong 1000000]),
game driven by scripted grid presses + deterministic `serve` + `tick`.
Timeline:
  reset -> RP=1 (right paddle top) -> LP=3 -> serve 1 0 -> 4x tick
    (ball 3->4->5->6->7, misses right paddle -> score 1 0, respawn)
  -> LP=1 (left paddle top) -> serve -1 0 -> 4x tick
    (ball 3->2->1->0, misses left paddle -> score 1 1)
  -> reset
Expected pinfo sequence exactly:
  reset | score 0 0 | score 1 0 | score 1 1 | reset | score 0 0
Run from this directory:  python3 build_test_pong.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=400)

PONG = p.obj(60, 60, "pong 1000000")
PLED = p.obj(60, 120, "print pled")
PINFO = p.obj(260, 120, "print pinfo")
p.connect(PONG, 0, PLED, 0)
p.connect(PONG, 1, PINFO, 0)

p.timeline(60, 200, [
    (100, "reset", PONG, 0),
    (200, "list 7 1 1", PONG, 0),
    (250, "list 0 3 1", PONG, 0),
    (300, "serve 1 0", PONG, 0),
    (400, "tick", PONG, 0),
    (500, "tick", PONG, 0),
    (600, "tick", PONG, 0),
    (700, "tick", PONG, 0),
    (800, "tick", PONG, 0),
    (900, "list 0 1 1", PONG, 0),
    (1000, "serve -1 0", PONG, 0),
    (1100, "tick", PONG, 0),
    (1200, "tick", PONG, 0),
    (1300, "tick", PONG, 0),
    (1400, "tick", PONG, 0),
    (1500, "reset", PONG, 0),
])

p.write("../test_pong.pd")
print("wrote test_pong.pd:", len(p.objs), "objects,", len(p.conns), "connections")
