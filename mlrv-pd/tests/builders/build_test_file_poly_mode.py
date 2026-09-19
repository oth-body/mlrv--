#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_file_poly_mode.pd (per-voice sample
parameters wiring item: verifies file_poly.pd's new top-level `mode
<voice> <loop|shot>` message actually reaches the right sample_voice~
instance, mirroring build_test_file_poly_gain_pitch.py's shape).

Two isolated, sequential single-voice capture windows (file_poly.pd sums
all voices into one outlet, so only one may sound per window), each twice
the loop length (N=4410, window=8820) to see both the playing phase and
whether it auto-stopped:
  voice 1, slot 0 (ramp fixture), default mode (loop)  -> capture_loop
  voice 2, slot 0, mode 2 shot sent first               -> capture_shot
stopall between windows for isolation.

Run from builders/: python3 build_test_file_poly_mode.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

N = 4410
WIN = 2 * N
p = Patch(w=1200, h=900)

lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\; pd dsp 1")
p.connect(lb, 0, dsp, 0)

fp = p.obj(20, 80, "file_poly")
pr = p.obj(20, 130, "print fp")
p.connect(fp, 1, pr, 0)

m_load = p.msg(100, 200, "load 0 /tmp/mlrv_fpmode_ramp.wav")
m_playv1 = p.msg(300, 200, f"playv 1 0 1 0 {N}")
m_playv2 = p.msg(300, 240, f"playv 2 0 1 0 {N}")
m_mode2 = p.msg(500, 200, "mode 2 shot")
m_stopall = p.msg(500, 240, "stopall")
for m in (m_load, m_playv1, m_playv2, m_mode2, m_stopall):
    p.connect(m, 0, fp, 0)

tw_loop = p.obj(700, 200, "tabwrite~ capture_loop")
tw_shot = p.obj(700, 240, "tabwrite~ capture_shot")
p.connect(fp, 0, tw_loop, 0)
p.connect(fp, 0, tw_shot, 0)

arm1 = p.obj(300, 400, "t b b")
arm2 = p.obj(300, 440, "t b b")
p.connect(arm1, 1, m_playv1, 0)
p.connect(arm1, 0, tw_loop, 0)
p.connect(arm2, 1, m_playv2, 0)
p.connect(arm2, 0, tw_shot, 0)

p.obj(20, 600, f"table capture_loop {WIN}")
p.obj(180, 600, f"table capture_shot {WIN}")

wmsg1 = p.msg(700, 700, "write /tmp/mlrv_fpmode_loop.wav capture_loop")
wr1 = p.obj(900, 700, "soundfiler")
p.connect(wmsg1, 0, wr1, 0)
wmsg2 = p.msg(700, 740, "write /tmp/mlrv_fpmode_shot.wav capture_shot")
wr2 = p.obj(900, 740, "soundfiler")
p.connect(wmsg2, 0, wr2, 0)

p.timeline(20, 800, [
    (50, None, m_load, 0),
    (200, None, arm1, 0),
    (1200, None, m_stopall, 0),
    (1250, None, m_mode2, 0),
    (1300, None, arm2, 0),
    (2300, None, wmsg1, 0),
    (2310, None, wmsg2, 0),
])

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_poly_mode.pd")
print("wrote test_file_poly_mode.pd")
