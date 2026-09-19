#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/record_buffer~.pd (1:1 mlrv recreation,
live audio recording item -- rec.maxpat equivalent).

Design: Max's [record~] maps directly onto Pd's [tabwrite~] (already
deeply understood in this codebase -- gotchas #11, #17), fed by whatever
signal the caller wires into this abstraction's signal inlet (adc~ for
live input, or a dac~ tap for resampling -- caller's choice, matching the
original's "live audio input (or resampled audio output)").

Playback of a recorded buffer deliberately reuses play_loop~.pd/
sample_voice~.pd/file_poly.pd UNCHANGED -- once a recording finishes, the
array it filled is playable through the exact same "set <arrayname>"
mechanism any other loaded sample uses. This abstraction only builds the
RECORDING half, which also means it never needs to touch file_poly.pd,
sample_voice~.pd, mapping.pd, or play_loop~.pd -- kept clear of those
files deliberately (peer sessions are mid-edit on all four for SHOT mode
and the tempo/clock item as of 2026-09-18).

Interface: signal inlet0 = audio in. Control inlet1: bare bang or
"record" (equivalent, both arm recording after any pending preroll),
"loop <0|1>" (1 = auto-rearm on completion, continual overwrite -- does
NOT re-apply preroll on subsequent loop iterations, only on the first
arm), "preroll <ms>" (delay between record and actually arming, default
0). outlet0 = signal passthrough. outlet1 = "done" bang, once per
completed pass.

Done-bang timing: duration_ms = arraySize / sampleRate * 1000, computed
ONCE at load (array size and sample rate never change mid-run) and
stored -- simpler than re-querying per recording, and simpler than SHOT
mode's version (no rate division needed; recording always runs at 1x).
Array size and sample rate are queried via [array size $1] / [samplerate~],
never trusted from a caller, same reasoning as play_loop~.pd's own
sampleRate query (gotcha #8).

Run from builders/: python3 build_record_buffer.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=800, h=600)

sig_in = p.obj(10, 20, "inlet~")
ctl_in = p.obj(250, 20, "inlet")
p.text(350, 20,
    "signal inlet0 = audio to record (feed it adc~ for live input or a "
    "dac~ tap for resampling \\, caller's choice \\, matching the "
    "original's \"live audio input (or resampled audio output)\"). "
    "control inlet1 accepts: bare bang or \"record\" (equivalent) -- arms "
    "recording now (after any pending preroll) \\; \"loop <0|1>\" -- 1 = "
    "auto-rearm on completion for continual overwrite recording (preroll "
    "only applies to the FIRST arm \\, not subsequent loop iterations) "
    "\\, default 0 (record once then stop) \\; \"preroll <ms>\" -- delay "
    "between record and the recording actually starting \\, default 0. "
    "outlet0 = signal passthrough (so this can sit inline without "
    "silencing the input) \\; outlet1 = done bang \\, once per completed "
    "pass. creation arg: record_buffer~ tableName -- caller must "
    "pre-declare [table tableName N] at whatever max length (samples) is "
    "wanted.")

sig_out = p.obj(10, 560, "outlet~")
done_out = p.obj(300, 560, "outlet")

route = p.obj(10, 60, "route bang record loop preroll")
p.connect(ctl_in, 0, route, 0)

tw = p.obj(10, 500, "tabwrite~ \\$1")
p.connect(sig_in, 0, sig_out, 0)
p.connect(sig_in, 0, tw, 0)

loop_store = p.obj(400, 100, "float 0")
p.connect(route, 2, loop_store, 1)  # "loop <0|1>" -> cold-set

preroll_delay = p.obj(10, 100, "delay 0")
p.connect(route, 3, preroll_delay, 1)  # "preroll <ms>" -> cold-set directly;
                                         # [delay]'s own right inlet retains
                                         # the last-set value, no separate
                                         # store object needed.
p.connect(route, 0, preroll_delay, 0)   # bang match -> arm (after preroll)
p.connect(route, 1, preroll_delay, 0)   # record match -> same path

# --- load-time computation of durationMS, once, never re-derived per recording ---
# duration_samples = arraySize / sampleRate: sampleRate is the denominator
# (cold inlet1, loaded first), arraySize the numerator (hot inlet0, must
# fire LAST to trigger the division with sampleRate already in place).
lb = p.obj(10, 160, "loadbang")
seq = p.obj(10, 200, "t b b")
srate = p.obj(150, 240, "samplerate~")
asize = p.obj(10, 240, "array size \\$1")
p.connect(lb, 0, seq, 0)
p.connect(seq, 1, srate, 0)   # fires first (rightmost outlet) -> denominator, cold
p.connect(seq, 0, asize, 0)   # fires last (leftmost outlet) -> numerator, hot

divide = p.obj(10, 280, "/")
p.connect(srate, 0, divide, 1)   # sampleRate -> cold inlet1, loaded first
p.connect(asize, 0, divide, 0)   # arraySize -> hot inlet0, triggers division
mul1000 = p.obj(10, 360, "* 1000")
p.connect(divide, 0, mul1000, 0)
duration_store = p.obj(10, 400, "float")
p.connect(mul1000, 0, duration_store, 1)  # cold-set once, permanent

# --- shared arm point: both the post-preroll path and loop re-arm feed here ---
arm = p.obj(200, 440, "t b b")
p.connect(preroll_delay, 0, arm, 0)

timer_delay = p.obj(400, 480, "delay 0")
duration_bang = p.obj(400, 440, "t b")
p.connect(arm, 1, duration_bang, 0)     # fires first (rightmost outlet)
p.connect(duration_bang, 0, duration_store, 0)  # re-emit stored duration
p.connect(duration_store, 0, timer_delay, 1)    # -> timer's time inlet, cold

p.connect(arm, 0, tw, 0)             # fires last (leftmost outlet) -> arm tabwrite~
p.connect(arm, 0, timer_delay, 0)    # -> also start the timer

p.connect(timer_delay, 0, done_out, 0)

# --- loop mode: on done, if loop=1, re-arm directly (bypasses preroll) ---
loop_check = p.obj(200, 500, "t b b")
p.connect(timer_delay, 0, loop_check, 0)
loop_bang = p.obj(200, 530, "t b")
p.connect(loop_check, 1, loop_bang, 0)  # fires first
p.connect(loop_bang, 0, loop_store, 0)  # re-emit stored loop flag
loop_sel = p.obj(200, 560, "select 1")
p.connect(loop_store, 0, loop_sel, 0)
p.connect(loop_sel, 0, arm, 0)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/abstractions/record_buffer~.pd")
print("wrote record_buffer~.pd")
