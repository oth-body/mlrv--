#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_file_poly_gain_pitch.pd (per-voice sample
parameters wiring item: verifies file_poly.pd's new top-level `gain <voice>
<value>` / `pitch <voice> <semitones>` messages actually reach the right
sample_voice~ instance, not just that they load clean).

Four isolated, sequential single-voice capture windows (file_poly.pd sums
all voices into one outlet, so only one voice may sound per window):
  voice 1, slot 0 (const fixture), default gain  -> capture_gain_default
  voice 2, slot 0, gain 2 0.5 sent first          -> capture_gain_half
  voice 3, slot 1 (ramp fixture), default pitch   -> capture_pitch_default
  voice 4, slot 1, pitch 4 12 sent first           -> capture_pitch_shifted
stopall between each window for isolation.

Run from builders/: python3 build_test_file_poly_gain_pitch.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

N = 2205
p = Patch(w=1200, h=900)

lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\\; pd dsp 1")
p.connect(lb, 0, dsp, 0)

fp = p.obj(20, 80, "file_poly")
pr = p.obj(20, 130, "print fp")
p.connect(fp, 1, pr, 0)

m_load_const = p.msg(100, 200, "load 0 /tmp/mlrv_fpgp_const.wav")
m_load_ramp = p.msg(100, 240, "load 1 /tmp/mlrv_fpgp_ramp.wav")

m_playv1 = p.msg(300, 200, f"playv 1 0 1 0 {N}")
m_playv2 = p.msg(300, 240, f"playv 2 0 1 0 {N}")
m_playv3 = p.msg(300, 280, f"playv 3 1 1 0 {N}")
m_playv4 = p.msg(300, 320, f"playv 4 1 1 0 {N}")
m_gain2 = p.msg(500, 200, "gain 2 0.5")
m_pitch4 = p.msg(500, 240, "pitch 4 12")
m_stopall = p.msg(500, 280, "stopall")
for m in (m_load_const, m_load_ramp, m_playv1, m_playv2, m_playv3, m_playv4,
          m_gain2, m_pitch4, m_stopall):
    p.connect(m, 0, fp, 0)

# each capture: bang tabwrite~ at the same instant its playv fires
tw_gd = p.obj(700, 200, "tabwrite~ capture_gain_default")
tw_gh = p.obj(700, 240, "tabwrite~ capture_gain_half")
tw_pd = p.obj(700, 280, "tabwrite~ capture_pitch_default")
tw_ps = p.obj(700, 320, "tabwrite~ capture_pitch_shifted")
p.connect(fp, 0, tw_gd, 0)
p.connect(fp, 0, tw_gh, 0)
p.connect(fp, 0, tw_pd, 0)
p.connect(fp, 0, tw_ps, 0)

arm1 = p.obj(300, 400, "t b b")
arm2 = p.obj(300, 440, "t b b")
arm3 = p.obj(300, 480, "t b b")
arm4 = p.obj(300, 520, "t b b")
p.connect(arm1, 1, m_playv1, 0)
p.connect(arm1, 0, tw_gd, 0)
p.connect(arm2, 1, m_playv2, 0)
p.connect(arm2, 0, tw_gh, 0)
p.connect(arm3, 1, m_playv3, 0)
p.connect(arm3, 0, tw_pd, 0)
p.connect(arm4, 1, m_playv4, 0)
p.connect(arm4, 0, tw_ps, 0)

# static array decls
p.obj(20, 600, f"table capture_gain_default {N}")
p.obj(180, 600, f"table capture_gain_half {N}")
p.obj(340, 600, f"table capture_pitch_default {N}")
p.obj(500, 600, f"table capture_pitch_shifted {N}")

writes = []
for name, path in (
    ("capture_gain_default", "/tmp/mlrv_fpgp_gain_default.wav"),
    ("capture_gain_half", "/tmp/mlrv_fpgp_gain_half.wav"),
    ("capture_pitch_default", "/tmp/mlrv_fpgp_pitch_default.wav"),
    ("capture_pitch_shifted", "/tmp/mlrv_fpgp_pitch_shifted.wav"),
):
    wmsg = p.msg(700, 700 + 40 * len(writes), f"write {path} {name}")
    wr = p.obj(900, 700 + 40 * len(writes), "soundfiler")
    p.connect(wmsg, 0, wr, 0)
    writes.append(wmsg)

p.timeline(20, 800, [
    (50, None, m_load_const, 0),
    (60, None, m_load_ramp, 0),
    (200, None, arm1, 0),
    (350, None, m_stopall, 0),
    (400, None, m_gain2, 0),
    (450, None, arm2, 0),
    (600, None, m_stopall, 0),
    (650, None, arm3, 0),
    (800, None, m_stopall, 0),
    (850, None, m_pitch4, 0),
    (900, None, arm4, 0),
    (1100, None, writes[0], 0),
    (1110, None, writes[1], 0),
    (1120, None, writes[2], 0),
    (1130, None, writes[3], 0),
])

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_poly_gain_pitch.pd")
print("wrote test_file_poly_gain_pitch.pd")
