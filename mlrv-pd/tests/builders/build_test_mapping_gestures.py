#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mapping_gestures.pd -- verifies
mapping.pd's grid gestures (user-picked direct-rows layout): y=6 buttons
(groupstop/pattern/record + LED flash/clear), y=5 group cycle with LED
readout and wrap, y=4 slave toggle proved BEHAVIORALLY (slaved trigger
held to the quantize grid, then immediate after un-slave -- same 220/280
pattern as run_mapping_slave_test.sh).

Run from builders/: python3 build_test_mapping_gestures.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1200, h=900)

mp = p.obj(60, 60, "mapping")
mc = p.obj(60, 140, "print mctrl")
p.connect(mp, 0, mc, 0)
led = p.obj(60, 200, "print led")
p.connect(mp, 1, led, 0)
pat = p.obj(60, 260, "print pat")
p.connect(mp, 3, pat, 0)
rec = p.obj(300, 260, "print rec")
p.connect(mp, 4, rec, 0)
rp = p.obj(300, 140, "route play")
p.connect(mp, 0, rp, 0)
pt = p.obj(300, 200, "timer")
ptb = p.obj(300, 230, "t b")
p.connect(rp, 0, ptb, 0)
p.connect(ptb, 0, pt, 1)
pms = p.obj(300, 290, "print play_ms")
p.connect(pt, 0, pms, 0)

IN0, IN1 = 0, 1
ev = [
    (100,  "loaded 3 4410", IN1, None),
    (150,  "list 3 4 1",    IN0, None),
    (220,  "list 3 7 1",    IN0, "press"),
    (600,  "list 3 4 1",    IN0, None),
    (700,  "list 3 7 1",    IN0, "press"),
    (900,  "list 2 6 1",    IN0, None),
    (1000, "list 2 6 0",    IN0, None),
    (1200, "list 4 6 1",    IN0, None),
    (1300, "list 5 6 1",    IN0, None),
    (1400, "list 6 6 1",    IN0, None),
    (1500, "list 7 6 1",    IN0, None),
    (1700, "list 2 5 1",    IN0, None),
    (1800, "list 2 5 1",    IN0, None),
    (1900, "list 2 5 1",    IN0, None),
    (2000, "list 2 5 1",    IN0, None),
    (2100, "list 2 5 1",    IN0, None),
]
lb = p.obj(900, 20, "loadbang")
tt = p.obj(900, 60, "t " + " ".join(["b"] * len(ev)))
p.connect(lb, 0, tt, 0)
for i, (delay_ms, msg_text, inlet, tag) in enumerate(ev):
    d = p.obj(60 + 80 * (i % 12), 500 + 70 * (i // 12), f"delay {delay_ms}")
    p.connect(tt, i, d, 0)
    m = p.msg(60 + 80 * (i % 12), 535 + 70 * (i // 12), msg_text)
    if tag == "press":
        tb = p.obj(60 + 80 * (i % 12), 575 + 70 * (i // 12), "t b b")
        p.connect(d, 0, tb, 0)
        p.connect(tb, 1, pt, 0)
        p.connect(tb, 0, m, 0)
        p.connect(m, 0, mp, inlet)
    else:
        p.connect(d, 0, m, 0)
        p.connect(m, 0, mp, inlet)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_mapping_gestures.pd")
print("wrote test_mapping_gestures.pd")
