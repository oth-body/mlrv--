#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mlrv_gui.pd -- increment-2 verification
(1:1 mlrv recreation, item 5 mapping GUI): the SAME bytes GUI widgets emit,
sent headlessly (widgets can't move without a display), driving the REAL
engine with captured-audio proof, plus a live-UDP OSC leg:

A. mapper path: `learn vgain1` + `ctl 0 30 0.25` -> `gain 1 0.5` into a
   real file_poly playing a const-16000 loop -> capture peak ~8000.
B. OSC leg: real UDP `/mlrv/ctl` packet -> osc_ctl -> mapper (sgroup0
   bound via direct learn) -> exact `group 0 2` dispatch print.
C. widget-direct path: the literal `gain 1 0.5` bytes a vgain hsl emits
   (same fmt table -- mapper_params) -> same capture assert as A.
D. mode widget bytes: `mode 1 shot` -> second-half silence vs first-half
   signal over a 2-period window (loop would repeat).
E. mlrv-gui.pd itself loads clean (widgets + engine + all 3 adapters).

Record path is NOT re-proven here (run_record_buffer_test.sh owns it);
the GUI record button emits the identical `record` bytes.

Run from builders/: python3 build_test_mlrv_gui.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1400, h=900)

mp = p.obj(60, 60, "mapper")
fp = p.obj(300, 60, "file_poly")
oscc = p.obj(560, 60, "osc_ctl 9007")
p.connect(oscc, 0, mp, 0)
dsp = p.msg(900, 100, "\\; pd dsp 1")
p.connect(p.obj(900, 60, "loadbang"), 0, dsp, 0)

p.connect(mp, 0, fp, 0)
dprint = p.obj(60, 140, "print disp")
p.connect(mp, 0, dprint, 0)

capA = p.obj(300, 200, "tabwrite~ gui_capA")
p.connect(fp, 0, capA, 0)
arrA = p.obj(300, 240, "table gui_capA 16000")
wrA = p.obj(300, 280, "soundfiler")
wmsgA = p.msg(300, 320, "write /tmp/mlrv_gui_capA.wav gui_capA")
p.connect(wmsgA, 0, wrA, 0)
capB = p.obj(560, 200, "tabwrite~ gui_capB")
p.connect(fp, 0, capB, 0)
arrB = p.obj(560, 240, "table gui_capB 16000")
wrB = p.obj(560, 280, "soundfiler")
wmsgB = p.msg(560, 320, "write /tmp/mlrv_gui_capB.wav gui_capB")
p.connect(wmsgB, 0, wrB, 0)
capD = p.obj(820, 200, "tabwrite~ gui_capD")
p.connect(fp, 0, capD, 0)
arrD = p.obj(820, 240, "table gui_capD 24000")
wrD = p.obj(820, 280, "soundfiler")
wmsgD = p.msg(820, 320, "write /tmp/mlrv_gui_capD.wav gui_capD")
p.connect(wmsgD, 0, wrD, 0)

ev = [
    (100,  "load 0 /tmp/mlrv_gui_const.wav", "fp"),
    (300,  "learn vgain1", "mp"),
    (400,  "ctl 0 30 0.25", "mp"),
    (450,  "ctl 0 30 0.25", "mp"),
    (500,  "playv 1 0 1 0 4410", "fp"),
    (500,  None, "capA"),
    (1500, None, "wrA"),
    (1700, "gain 1 0.5", "fp"),
    (1800, "playv 1 0 1 0 4410", "fp"),
    (1800, None, "capB"),
    (2800, None, "wrB"),
    (3000, "mode 1 shot", "fp"),
    (3100, "playv 1 0 1 0 4410", "fp"),
    (3100, None, "capD"),
    (3800, None, "wrD"),
    (4000, "learn sgroup0", "mp"),
]
lb = p.obj(900, 20, "loadbang")
tt = p.obj(900, 60, "t " + " ".join(["b"] * len(ev)))
p.connect(lb, 0, tt, 0)
for i, (delay_ms, msg_text, tgt) in enumerate(ev):
    d = p.obj(60 + 60 * i, 500, f"delay {delay_ms}")
    p.connect(tt, i, d, 0)
    if msg_text is None:
        w = {"capA": capA, "wrA": wmsgA, "capB": capB, "wrB": wmsgB,
             "capD": capD, "wrD": wmsgD}[tgt]
        p.connect(d, 0, w, 0)
    else:
        m = p.msg(60 + 60 * i, 560, msg_text)
        p.connect(d, 0, m, 0)
        p.connect(m, 0, mp if tgt == "mp" else fp, 0)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_mlrv_gui.pd")
print("wrote test_mlrv_gui.pd")
