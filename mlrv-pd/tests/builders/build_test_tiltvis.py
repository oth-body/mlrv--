#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_tiltvis.pd. Deterministic, no hardware:
  tilt +x -> bubble right edge; press -> recenter; tilt -x -> left edge.
Run from this directory:  python3 build_test_tiltvis.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=400)

TV = p.obj(60, 60, "tiltvis")
TLED = p.obj(60, 120, "print tled")
TINFO = p.obj(260, 120, "print tinfo")
p.connect(TV, 0, TLED, 0)
p.connect(TV, 1, TINFO, 0)

p.timeline(60, 200, [
    (100, "tilt 177 127 127", TV, 0),
    (300, "list 0 0 1", TV, 0),
    (500, "tilt 127 127 127", TV, 0),
])

p.write("../test_tiltvis.pd")
print("wrote test_tiltvis.pd:", len(p.objs), "objects,", len(p.conns), "connections")
