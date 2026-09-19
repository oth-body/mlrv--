#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
p = Patch(w=1200, h=800)
# mapping -> file_browser -> file_poly
mapping = p.obj(20, 20, "mapping")
fb = p.obj(200, 20, "file_browser")
fpoly = p.obj(400, 20, "file_poly")
p.connect(mapping, 5, fb, 0)
p.connect(fb, 0, fpoly, 0)
# prints
fb_out = p.obj(200, 80, "print fb_load")
p.connect(fb, 0, fb_out, 0)
fp_info = p.obj(400, 80, "print fp_info")
p.connect(fpoly, 1, fp_info, 0)
# file list display (not needed for headless)
# timeline: add file, slot select via grid, file select via grid
lb = p.obj(20, 120, "loadbang")
# Use timeline via t
events = [
    (50, "add /tmp/fb_test0.wav", fb, 0),
    (100, "add /tmp/fb_test1.wav", fb, 0),
    (150, "list 2 3 1", mapping, 0),  # y=3 x=2 -> slot 2
    (200, "list 0 2 1", mapping, 0),  # y=2 x=0 -> file 0 + load
    (300, "list 5 3 1", mapping, 0),  # y=3 x=5 -> slot 5
    (350, "list 1 2 1", mapping, 0),  # y=2 x=1 -> file 1 + load
]
tt = p.obj(20, 120, "t " + " ".join(["b"]*len(events)))
p.connect(lb, 0, tt, 0)
for i,(dly, txt, tgt, inlet) in enumerate(events):
    d = p.obj(20+80*i, 200, f"delay {dly}")
    p.connect(tt, i, d, 0)
    m = p.msg(20+80*i, 240, txt)
    p.connect(d, 0, m, 0)
    p.connect(m, 0, tgt, inlet)
p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_browser_grid.pd")
print("wrote test_file_browser_grid")
