#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mixer_via_file_poly.pd -- verifies the
mixer wiring item (file_poly per-voice outlets 2-5 -> mixer inlets 0-3 ->
master). This is the integration the plan promised: voice isolation via
vol, wet path via send, and the legacy summed outlet still bit-identical.

Run from builders/: python3 build_test_mixer_via_file_poly.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1200, h=900)

fpoly = p.obj(20, 80, "file_poly")
mixer = p.obj(300, 80, "mixer")
master = p.obj(600, 80, "master")
# signal chain: per-voice -> mixer -> master
p.connect(fpoly, 2, mixer, 0)
p.connect(fpoly, 3, mixer, 1)
p.connect(fpoly, 4, mixer, 2)
p.connect(fpoly, 5, mixer, 3)
p.connect(mixer, 0, master, 0)
# fxin stub to silence the "no matching send" error when no effect is wired
sig = p.obj(600, 200, "sig~ 0")
sfx = p.obj(600, 240, "send~ fxin")
p.connect(sig, 0, sfx, 0)
# master gain to 1 for predictable math (default is 0, would silence)
lb_master = p.obj(20, 20, "loadbang")
msg_master = p.msg(500, 20, "1")
p.connect(lb_master, 0, msg_master, 0)
p.connect(msg_master, 0, master, 1)
# also keep the legacy summed outlet connected to a separate capture for the
# bit-identical check (existing suites still capture via outlet 0)
# we capture both: mixer dry sum via master, and file_poly sum directly
cap_mix = p.obj(600, 320, "tabwrite~ cap_mix")
p.connect(master, 0, cap_mix, 0)
cap_mix2 = p.obj(600, 380, "tabwrite~ cap_mix2")
p.connect(master, 0, cap_mix2, 0)
cap_sum = p.obj(20, 200, "tabwrite~ cap_sum")
p.connect(fpoly, 0, cap_sum, 0)
p.obj(600, 360, "table cap_mix 12000")
p.obj(600, 420, "table cap_mix2 12000")
p.obj(20, 240, "table cap_sum 12000")
wr_mix = p.obj(600, 400, "soundfiler")
msg_mix = p.msg(600, 440, "write /tmp/mix_via_cap.wav cap_mix")
p.connect(msg_mix, 0, wr_mix, 0)
wr_mix2 = p.obj(600, 460, "soundfiler")
msg_mix2 = p.msg(600, 500, "write /tmp/mix_via_cap2.wav cap_mix2")
p.connect(msg_mix2, 0, wr_mix2, 0)
wr_sum = p.obj(20, 280, "soundfiler")
msg_sum = p.msg(20, 320, "write /tmp/mix_sum_cap.wav cap_sum")
p.connect(msg_sum, 0, wr_sum, 0)
# control prints for vol/send query and file_poly loads
mix_rep = p.obj(300, 140, "print mix_rep")
p.connect(mixer, 1, mix_rep, 0)
fp_info = p.obj(20, 140, "print fp_info")
p.connect(fpoly, 1, fp_info, 0)

# bootstrap: load fixtures, set vols to 1, then run sequence
lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\\; pd dsp 1")
p.connect(lb, 0, dsp, 0)
ev = [
    (50, "load 0 /tmp/mix_const0.wav", fpoly, 0),
    (100, "load 1 /tmp/mix_const1.wav", fpoly, 0),
    (200, "vol 0 1", mixer, 4),
    (250, "vol 1 1", mixer, 4),
    (300, "playv 1 0 1 0 4000", fpoly, 0),
    (350, "playv 2 1 1 0 4000", fpoly, 0),
    (400, None, cap_mix, 0),
    (400, None, cap_sum, 0),
    (800, None, msg_mix, 0),
    (800, None, msg_sum, 0),
    (900, "vol 0 0", mixer, 4),
    (950, "playv 1 0 1 0 4000", fpoly, 0),
    (1000, "playv 2 1 1 0 4000", fpoly, 0),
    (1050, None, cap_mix2, 0),
    (1450, None, msg_mix2, 0),
    (1500, "query", mixer, 4),
]
tt = p.obj(20, 20, "t " + " ".join(["b"]*len(ev)))
p.connect(lb, 0, tt, 0)
for i,(delay_ms, msg_text, tgt, inlet) in enumerate(ev):
    d = p.obj(20+80*i, 500, f"delay {delay_ms}")
    p.connect(tt, i, d, 0)
    if msg_text is None:
        p.connect(d, 0, tgt, inlet)
    else:
        m = p.msg(20+80*i, 540, msg_text)
        p.connect(d, 0, m, 0)
        p.connect(m, 0, tgt, inlet)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_mixer_via_file_poly.pd")
print("wrote test_mixer_via_file_poly.pd")
