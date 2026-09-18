#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_master_query.pd (presets prerequisite).

Control-only test, no audio: instantiates master, queries the default gain,
sets two gains, queries again. Query responses are bare floats, directly
replayable into the gain inlet (that replayability is the point for presets).

Run from builders/: python3 build_test_master_query.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=500)

MASTER = p.obj(20, 120, "master")
QPRINT = p.obj(20, 170, "print q")
p.connect(MASTER, 2, QPRINT, 0)
# match master's internal buses so the load is error-free
p.obj(300, 120, "receive~ fxout")
STUB = p.obj(300, 160, "sig~ 0")
FXIN = p.obj(300, 200, "send~ fxin")
p.connect(STUB, 0, FXIN, 0)

events = [
    (50, "query", MASTER, 1),
    (100, "0.8", MASTER, 1),
    (150, "query", MASTER, 1),
    (200, "0.5", MASTER, 1),
    (250, "query", MASTER, 1),
    (300, "\\; pd quit", MASTER, 0),
]
p.timeline(20, 250, events)

p.write("../test_master_query.pd")
print("wrote test_master_query.pd:", len(p.objs), "objects,", len(p.conns), "connections")
