#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mixer_query.pd (presets prerequisite).

Control-only test, no audio fixtures: instantiates mixer, queries defaults,
sets a spread of vols/sends (exactly-representable floats only, so the
runner can assert exact strings), sends an out-of-range vol (ignored),
queries again. Query lines must be byte-exact and replayable as control
messages (that replayability is the whole point for presets).

Run from builders/: python3 build_test_mixer_query.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=500)

MIXER = p.obj(20, 120, "mixer")
QPRINT = p.obj(20, 170, "print q")
p.connect(MIXER, 1, QPRINT, 0)
RECV_FXOUT = p.obj(300, 120, "receive~ fxout")  # match mixer's send~ fxout, no error

events = [
    (50, "query", MIXER, 4),
    (100, "vol 0 0.5", MIXER, 4),
    (110, "vol 2 0.25", MIXER, 4),
    (120, "send 1 0.5", MIXER, 4),
    (130, "send 3 0.125", MIXER, 4),
    (140, "vol 9 0.5", MIXER, 4),
    (200, "query", MIXER, 4),
    (300, "\\; pd quit", MIXER, 0),
]
p.timeline(20, 250, events)

p.write("../test_mixer_query.pd")
print("wrote test_mixer_query.pd:", len(p.objs), "objects,", len(p.conns), "connections")
