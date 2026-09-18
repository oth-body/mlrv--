#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_file_poly_unload.pd (sample-memory item).

Timeline (all delays ms from load):
  load 0 <ramp 4410> -> loaded 0 4410
  load 3 <const 2205> -> loaded 3 2205
  query               -> 8-line ascending dump (tracked occupancy)
  unload 3            -> loaded 3 0; slot silenced + shrunk to 64
  probes              -> size mlrv-sample-3 == 64, cells 0/63 == 0
  query               -> dump again (slot 3 now 0, rest unchanged)
  unload 9            -> out of range: nothing, no error
  playv 1 3 ...       -> capture proves the emptied slot plays silence
  write capture wav
  load 3 <const>      -> slot reusable (loaded 3 2205, size back to 2205)
  probes + stopall

Run from builders/: python3 build_test_file_poly_unload.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1200, h=900)

lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\\; pd dsp 1")
p.connect(lb, 0, dsp, 0)

fp = p.obj(20, 80, "file_poly")
pr = p.obj(20, 130, "print fp")
p.connect(fp, 1, pr, 0)

# capture tap on the summed audio outlet
cap = p.obj(560, 1100, "table capture 4410")
tw = p.obj(200, 520, "tabwrite~ capture")
p.connect(fp, 0, tw, 0)
wr = p.obj(560, 460, "soundfiler")
wmsg = p.msg(560, 400, "write /tmp/mlrv_fp_unload_cap.wav capture")

# probes (static): size + two cells of slot 3
trz = p.obj(200, 300, "tabread mlrv-sample-3")
m0 = p.msg(140, 260, "0")
m63 = p.msg(260, 260, "63")
prz = p.obj(200, 340, "print cell")
sz = p.obj(500, 300, "array size mlrv-sample-3")
psz = p.obj(500, 340, "print size")
p.connect(m0, 0, trz, 0)
p.connect(m63, 0, trz, 0)
p.connect(trz, 0, prz, 0)
p.connect(sz, 0, psz, 0)
probes = p.obj(200, 220, "t b b b")
p.connect(probes, 2, m0, 0)
p.connect(probes, 1, m63, 0)
p.connect(probes, 0, sz, 0)

# control messages
m_load0 = p.msg(100, 500, "load 0 /tmp/mlrv_fp_long.wav")
m_load3 = p.msg(100, 560, "load 3 /tmp/mlrv_fp_short.wav")
m_q1 = p.msg(100, 620, "query")
m_un3 = p.msg(100, 680, "unload 3")
m_q2 = p.msg(100, 740, "query")
m_un9 = p.msg(100, 800, "unload 9")
m_play = p.msg(100, 860, "playv 1 3 1 0 64")
m_stop = p.msg(100, 920, "stopall")
for m in (m_load0, m_load3, m_q1, m_un3, m_q2, m_un9, m_play, m_stop):
    p.connect(m, 0, fp, 0)

# play + arm capture in the same tick
playarm = p.obj(100, 900, "t b b")
p.connect(playarm, 1, m_play, 0)
p.connect(playarm, 0, tw, 0)

p.timeline(20, 1000, [
    (50, None, m_load0, 0),
    (150, None, m_load3, 0),
    (250, None, m_q1, 0),
    (350, None, m_un3, 0),
    (450, None, probes, 0),
    (550, None, m_q2, 0),
    (650, None, m_un9, 0),
    (750, None, playarm, 0),
    (1100, None, wmsg, 0),
    (1200, None, m_load3, 0),
    (1300, None, probes, 0),
    (1400, None, m_stop, 0),
])
p.connect(wmsg, 0, wr, 0)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_poly_unload.pd")
print("wrote test_file_poly_unload.pd")
