#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
p = Patch(w=600, h=400)
fb = p.obj(20, 20, "file_browser")
pr = p.obj(20, 80, "print fb_out")
p.connect(fb, 0, pr, 0)
lb = p.obj(20, 120, "loadbang")
# Use timeline for ordered messages
events = [
    (50, "add /tmp/test.wav", fb, 0),
    (100, "slot 3", fb, 0),
    (150, "load", fb, 0),
    (200, "add /tmp/other.wav", fb, 0),
    (250, "slot 5", fb, 0),
    (300, "load", fb, 0),
    (350, "clear", fb, 0),
    (400, "slot 1", fb, 0),
    (450, "load", fb, 0),  # should be silent or not load after clear
]
tt = p.obj(20, 120, "t " + " ".join(["b"]*len(events)))
p.connect(lb, 0, tt, 0)
for i,(dly, txt, tgt, inlet) in enumerate(events):
    d = p.obj(20+60*i, 200, f"delay {dly}")
    p.connect(tt, i, d, 0)
    m = p.msg(20+60*i, 240, txt)
    p.connect(d, 0, m, 0)
    p.connect(m, 0, tgt, inlet)
p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_browser.pd")
print("wrote test_file_browser")
