#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mapper.pd -- verifies mapper.pd's
binding core (1:1 mlrv recreation, item 5, increment 1): learn/bind/
steal/dispatch/min-edit/clear across all four param kinds (cont, dsym,
dint, trig), asserting exact dispatch bytes.

Mapper's contract is control-plane messages (engine DSP lives in the
suites of file_poly/mixer/master/clock), so message-exactness plus
binding semantics IS the real behavior here. Full audio end-to-end
(GUI widget -> engine -> captured sound) belongs to increment 2.

Run from builders/: python3 build_test_mapper.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1200, h=900)

mp = p.obj(60, 60, "mapper")
r = p.obj(60, 140, "route tempo vol gain mode group groupstop")
p.connect(mp, 0, r, 0)
for i, fam in enumerate(["t_tempo", "t_vol", "t_gain", "t_mode", "t_group", "t_groupstop"]):
    pr = p.obj(60 + 130 * i, 200, f"print {fam}")
    p.connect(r, i, pr, 0)
pm = p.obj(60 + 130 * 6, 200, "print t_master")
p.connect(r, 6, pm, 0)

IN0 = 0
ev = [
    (100,  "learn tempo",      None),
    (200,  "ctl 0 16 0.5",     None),
    (300,  "ctl 0 16 0.25",    None),
    (400,  "ctl 0 17 0.5",     None),
    (500,  "min tempo 100",    None),
    (600,  "ctl 0 16 0.5",     None),
    (700,  "learn master",     None),
    (800,  "ctl 0 16 1",       None),
    (900,  "ctl 0 16 1",       None),
    (1000, "clear master",     None),
    (1100, "ctl 0 16 1",       None),
    (1200, "learn vmode1",     None),
    (1300, "ctl 1 3 0.9",      None),
    (1350, "ctl 1 3 1",        None),
    (1400, "ctl 1 3 0.1",      None),
    (1500, "learn groupstop1", None),
    (1600, "ctl 2 5 1",        None),
    (1650, "ctl 2 5 1",        None),
    (1700, "learn sgroup0",    None),
    (1800, "ctl 0 20 0.6",     None),
    (1850, "ctl 0 20 0.6",     None),
    (1900, "ctl 0 20 5",       None),
    (2000, "learn vgain1",     None),
    (2100, "ctl 0 30 0.5",     None),
    (2150, "ctl 0 30 0.5",     None),
]
lb = p.obj(900, 20, "loadbang")
tt = p.obj(900, 60, "t " + " ".join(["b"] * len(ev)))
p.connect(lb, 0, tt, 0)
for i, (delay_ms, msg_text, _) in enumerate(ev):
    col_x = 60 + 80 * (i % 12)
    row_y = 640 + 70 * (i // 12)
    d = p.obj(col_x, row_y, f"delay {delay_ms}")
    p.connect(tt, i, d, 0)
    m = p.msg(col_x, row_y + 35, msg_text)
    p.connect(d, 0, m, 0)
    p.connect(m, 0, mp, IN0)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_mapper.pd")
print("wrote test_mapper.pd")
