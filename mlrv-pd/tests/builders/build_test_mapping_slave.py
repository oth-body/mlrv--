#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_mapping_slave.pd -- verifies mapping.pd's
slave wiring (1:1 mlrv recreation, item 2) against real elapsed time (Pd's
own [timer]), not just message order:

- slaved slot press -> LED immediate, `play ...` held to the quantize grid
  (default 120bpm/1 beat = 500ms; press at 220ms -> release ~280ms later,
  mirroring run_clock_test.sh's own numbers and tolerance);
- unslaved press -> play immediate;
- un-slave -> immediate again; out-of-range `slave 9 1` ignored;
- `tempo 240` forwarded into the contained clock (beat-pulse intervals halve
  to ~250ms, steady-state -- asserts nothing about metro's ambiguous
  mid-flight rescheduling, only the settled rate);
- `quantize 2` forwarded (intervals double back to ~500ms).

Run from builders/: python3 build_test_mapping_slave.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=1200, h=900)

mp = p.obj(60, 60, "mapping")

mctrl = p.obj(60, 140, "print mctrl")
p.connect(mp, 0, mctrl, 0)
rplay = p.obj(280, 140, "route play")
p.connect(mp, 0, rplay, 0)
play_tb = p.obj(280, 170, "t b")
p.connect(rplay, 0, play_tb, 0)
play_timer = p.obj(280, 200, "timer")
p.connect(play_tb, 0, play_timer, 1)
play_ms = p.obj(280, 260, "print play_ms")
p.connect(play_timer, 0, play_ms, 0)

led = p.obj(60, 320, "print led")
p.connect(mp, 1, led, 0)
led_tb = p.obj(280, 290, "t b")
p.connect(mp, 1, led_tb, 0)
led_timer = p.obj(280, 320, "timer")
p.connect(led_tb, 0, led_timer, 1)
led_ms = p.obj(280, 380, "print led_ms")
p.connect(led_timer, 0, led_ms, 0)

beat = p.obj(60, 440, "print beat")
p.connect(mp, 2, beat, 0)
sp1 = p.obj(280, 440, "spigot")
p.connect(mp, 2, sp1, 0)
bt1 = p.obj(280, 500, "timer")
t1a = p.obj(280, 560, "t b b")
p.connect(sp1, 0, t1a, 0)
p.connect(t1a, 1, bt1, 1)
p.connect(t1a, 0, bt1, 0)
iv1 = p.obj(280, 620, "print int1_ms")
p.connect(bt1, 0, iv1, 0)
sp2 = p.obj(560, 440, "spigot")
p.connect(mp, 2, sp2, 0)
bt2 = p.obj(560, 500, "timer")
t2a = p.obj(560, 560, "t b b")
p.connect(sp2, 0, t2a, 0)
p.connect(t2a, 1, bt2, 1)
p.connect(t2a, 0, bt2, 0)
iv2 = p.obj(560, 620, "print int2_ms")
p.connect(bt2, 0, iv2, 0)

IN0, IN1 = 0, 1
ev = [
    (0,    "loaded 0 4410", IN1, None),
    (0,    "loaded 1 4410", IN1, None),
    (0,    "slave 0 1",     IN0, None),
    (220,  "list 0 7 1",    IN0, "press1"),
    (900,  "list 1 7 1",    IN0, "press2"),
    (1300, "slave 0 0",     IN0, None),
    (1400, "list 0 7 1",    IN0, "press3"),
    (1700, "slave 9 1",     IN0, None),
    (1800, "list 0 7 1",    IN0, "press4"),
    (2100, "tempo 240",     IN0, None),
    (3300, "1",             None, "spigot1"),
    (4800, "quantize 2",    IN0, None),
    (6000, "1",             None, "spigot2"),
]
lb = p.obj(800, 20, "loadbang")
tt = p.obj(800, 60, "t " + " ".join(["b"] * len(ev)))
p.connect(lb, 0, tt, 0)
for i, (delay_ms, msg_text, inlet, tag) in enumerate(ev):
    col_x = 60 + 80 * (i % 12)
    row_y = 700 + 70 * (i // 12)
    d = p.obj(col_x, row_y, f"delay {delay_ms}")
    p.connect(tt, i, d, 0)
    m = p.msg(col_x, row_y + 35, msg_text)
    if tag == "spigot1":
        p.connect(d, 0, m, 0)
        p.connect(m, 0, sp1, 1)
    elif tag == "spigot2":
        p.connect(d, 0, m, 0)
        p.connect(m, 0, sp2, 1)
    elif tag is not None and tag.startswith("press"):
        tb = p.obj(col_x, row_y + 70, "t b b b")
        p.connect(d, 0, tb, 0)
        p.connect(tb, 2, play_timer, 0)
        p.connect(tb, 1, led_timer, 0)
        p.connect(tb, 0, m, 0)
        p.connect(m, 0, mp, inlet)
    else:
        p.connect(d, 0, m, 0)
        p.connect(m, 0, mp, inlet)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_mapping_slave.pd")
print("wrote test_mapping_slave.pd")
