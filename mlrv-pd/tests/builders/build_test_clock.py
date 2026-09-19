#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_clock.pd -- verifies clock.pd's default
tempo/quantize computation and the quantize-gate mechanism against real
elapsed time (Pd's own [timer]), not just message-arrival order.

Scope note: this only tests the DEFAULT state (120bpm, quantize 1 beat =
500ms grid), the same scenario the abstraction was probe-verified
against before being written. Verifying a tempo CHANGE mid-flight
against [metro]'s own interval-change/rescheduling semantics turned out
to be a genuinely ambiguous timing question (does a new interval affect
the tick already pending, or only subsequent gaps?) that would need its
own dedicated probe to answer honestly -- deliberately deferred rather
than asserting a specific behavior that wasn't actually verified.

Run from builders/: python3 build_test_clock.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=500, h=300)

lb = p.obj(20, 20, "loadbang")
clk = p.obj(20, 60, "clock")
p.connect(lb, 0, clk, 0)

pr_released = p.obj(20, 100, "print released")
timer1 = p.obj(200, 20, "timer")
pr_elapsed = p.obj(200, 60, "print elapsed_ms")
p.connect(clk, 0, pr_released, 0)
p.connect(clk, 0, timer1, 1)  # report elapsed at the moment of release
p.connect(timer1, 0, pr_elapsed, 0)

trig_delay = p.obj(400, 20, "delay 220")
trig_bang = p.msg(400, 60, "bang")
p.connect(lb, 0, trig_delay, 0)
p.connect(trig_delay, 0, trig_bang, 0)
p.connect(trig_bang, 0, clk, 0)
p.connect(trig_bang, 0, timer1, 0)  # start stopwatch at trigger time

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/clock-subsystem/mlrv-pd/tests/test_clock.pd")
print("wrote test_clock.pd")
