#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_pattern_recorder.pd -- verifies
pattern_recorder.pd's record -> auto-stop -> playback -> loop -> stop
cycle against real elapsed time and real event content, not just
message order.

Timeline: arm at t=60, event1 at t=100 (starts recording, delay 0),
event2 at t=200 (100ms after event1). length=300ms, so auto-stop fires
~300ms after event1 (t=400 from load), starting playback. One
continuously-running timer (started at load, never reset) reports
absolute elapsed-since-load at every playback event -- expected:
lap1 (400, 500), lap2 (500, 600) [looping is seamless: qlist's done-bang
fires immediately after the last message with no built-in gap, so a
new lap's first event lands at the exact same instant as the previous
lap's last event, confirmed empirically, not assumed]. `stop` is sent
at t=650 (mid-lap-2, after its first event at 600 but before its
second at 700) to verify no further playback events fire once stopped.

Run from builders/: python3 build_test_pattern_recorder.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=700, h=500)

lb = p.obj(20, 20, "loadbang")
pr = p.obj(20, 60, "pattern_recorder")

m_length = p.msg(20, 100, "length 300")
m_arm = p.msg(120, 100, "arm")
m_ev1 = p.msg(220, 100, "2 3 1")
m_ev2 = p.msg(320, 100, "4 5 0")
m_stop = p.msg(420, 100, "stop")

for m in (m_length, m_arm, m_ev1, m_ev2, m_stop):
    p.connect(m, 0, pr, 0)

live_pr = p.obj(500, 60, "print live")
p.connect(pr, 1, live_pr, 0)

playback_pr = p.obj(500, 100, "print playback")
p.connect(pr, 0, playback_pr, 0)

playback_bang = p.obj(500, 130, "t b")
p.connect(pr, 0, playback_bang, 0)

master_timer = p.obj(500, 170, "timer")
p.connect(lb, 0, master_timer, 0)
p.connect(playback_bang, 0, master_timer, 1)
elapsed_pr = p.obj(500, 210, "print elapsed_since_load")
p.connect(master_timer, 0, elapsed_pr, 0)

# counter idiom, gotcha-23-compliant: bang count's HOT inlet to read+emit its
# CURRENT value, add 1, store the result back via count's COLD inlet (silent).
# Storing back via the hot inlet instead creates a genuine infinite feedback
# loop -- found the hard way ("error: stack overflow", count reaching 498
# within one test run before overflowing) -- fixed, not guessed at.
count = p.obj(700, 60, "float 0")
inc = p.obj(700, 100, "+ 1")
p.connect(playback_bang, 0, count, 0)
p.connect(count, 0, inc, 0)
p.connect(inc, 0, count, 1)
count_pr = p.obj(700, 140, "print playback_count")
p.connect(inc, 0, count_pr, 0)

p.timeline(20, 300, [
    (20, None, m_length, 0),
    (60, None, m_arm, 0),
    (100, None, m_ev1, 0),
    (200, None, m_ev2, 0),
    (650, None, m_stop, 0),
])

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/pattern-recorder/mlrv-pd/tests/test_pattern_recorder.pd")
print("wrote test_pattern_recorder.pd")
