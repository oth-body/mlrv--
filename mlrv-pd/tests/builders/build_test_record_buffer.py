#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_record_buffer.pd (1:1 mlrv recreation,
live audio recording item).

Verifies, against real captured audio and real timing, not just a clean
load:
  - a bare bang starts recording, and the recorded content is the REAL
    input signal (osc~ 100Hz), not silence -- checked by writing the
    recorded array to a WAV and inspecting its actual samples.
  - the done-bang fires (proves the load-time duration_ms computation
    and the timer chain work end to end).
  - "record" (the word) is equivalent to a bare bang.
  - preroll delays the FIRST arm: with preroll 300ms on a ~9ms recording,
    nothing should be captured (array stays at its initial zero state)
    before ~300ms elapses, and should be captured shortly after.
  - loop mode re-arms automatically: counts done-bangs over a fixed
    window and checks the count is in the right ballpark for the known
    per-cycle duration (441 samples / real engine samplerate).

Run from builders/: python3 build_test_record_buffer.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

N = 441  # ~9ms at 48kHz -- deliberately short so loop-mode cycles many times
         # within a short, fast-running test window
p = Patch(w=900, h=700)

lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\\; pd dsp 1")
p.connect(lb, 0, dsp, 0)

osc = p.obj(20, 60, "osc~ 100")

# --- basic recording: bare bang ---
rb_a = p.obj(20, 100, f"record_buffer~ recbuf_a")
p.obj(20, 150, f"table recbuf_a {N}")
p.connect(osc, 0, rb_a, 0)
m_bang_a = p.msg(200, 100, "bang")
p.connect(m_bang_a, 0, rb_a, 1)
pr_done_a = p.obj(400, 100, "print done_a")
p.connect(rb_a, 1, pr_done_a, 0)
m_write_a = p.msg(600, 100, "write /tmp/mlrv_recbuf_a.wav recbuf_a")
sf_a = p.obj(750, 100, "soundfiler")
p.connect(m_write_a, 0, sf_a, 0)

# --- "record" (word) equivalence ---
rb_b = p.obj(20, 180, f"record_buffer~ recbuf_b")
p.obj(20, 230, f"table recbuf_b {N}")
p.connect(osc, 0, rb_b, 0)
m_record_b = p.msg(200, 180, "record")
p.connect(m_record_b, 0, rb_b, 1)
pr_done_b = p.obj(400, 180, "print done_b")
p.connect(rb_b, 1, pr_done_b, 0)

# --- preroll: recording should not start until ~300ms after the message ---
rb_c = p.obj(20, 260, f"record_buffer~ recbuf_c")
p.obj(20, 310, f"table recbuf_c {N}")
p.connect(osc, 0, rb_c, 0)
m_preroll = p.msg(200, 260, "preroll 300")
m_record_c = p.msg(300, 260, "record")
p.connect(m_preroll, 0, rb_c, 1)
p.connect(m_record_c, 0, rb_c, 1)
pr_done_c = p.obj(400, 260, "print done_c")
p.connect(rb_c, 1, pr_done_c, 0)
m_write_c_early = p.msg(600, 260, "write /tmp/mlrv_recbuf_c_early.wav recbuf_c")
sf_c_early = p.obj(750, 260, "soundfiler")
p.connect(m_write_c_early, 0, sf_c_early, 0)
m_write_c_late = p.msg(600, 300, "write /tmp/mlrv_recbuf_c_late.wav recbuf_c")
sf_c_late = p.obj(750, 300, "soundfiler")
p.connect(m_write_c_late, 0, sf_c_late, 0)

# --- loop mode: count done-bangs over a fixed window ---
rb_d = p.obj(20, 340, f"record_buffer~ recbuf_d")
p.obj(20, 390, f"table recbuf_d {N}")
p.connect(osc, 0, rb_d, 0)
m_loop_on = p.msg(200, 340, "loop 1")
m_record_d = p.msg(300, 340, "record")
p.connect(m_loop_on, 0, rb_d, 1)
p.connect(m_record_d, 0, rb_d, 1)
# classic Pd counter idiom: [f] emits its CURRENT value on its hot inlet
# (each done-bang), which feeds [+ 1] whose result is stored back into
# [f]'s COLD inlet only (never the hot inlet -- a self-feedback into the
# hot inlet creates a runaway same-tick loop, probe-verified the hard way
# before this was written into the real builder).
count_store = p.obj(400, 340, "f 0")
counter = p.obj(500, 340, "+ 1")
p.connect(rb_d, 1, count_store, 0)     # each done-bang -> hot, emits current count
p.connect(count_store, 0, counter, 0)
p.connect(counter, 0, count_store, 1)  # increment -> cold, stores for next time
count_bang = p.obj(600, 340, "t b")

m_loop_off = p.msg(300, 340, "loop 0")
p.connect(m_loop_off, 0, rb_d, 1)

p.timeline(20, 500, [
    (50, None, m_bang_a, 0),
    (100, None, m_record_b, 0),
    (150, None, m_preroll, 0),
    (160, None, m_record_c, 0),
    (200, None, m_write_c_early, 0),   # before preroll elapses -- expect zeros
    (700, None, m_write_c_late, 0),    # well after preroll+one cycle -- expect real signal
    (750, None, m_loop_on, 0),
    (760, None, m_record_d, 0),
    # loop mode free-runs from 760ms; a process-level `timeout` wrapper
    # doesn't stop it, and it keeps incrementing past any mid-run snapshot
    # (a real testing-methodology bug hit building this -- see CLAUDE.md).
    # Explicitly disable looping so the count settles at a final, stable
    # value instead of racing an external process kill.
    (1760, None, m_loop_off, 0),       # stop after ~1000ms of active looping
    (1800, None, count_bang, 0),       # read the now-settled final count
    (1810, None, m_write_a, 0),
])
p.connect(count_bang, 0, count_store, 0)  # bang to re-emit final count
final_print = p.obj(700, 380, "print loop_count_final")
p.connect(count_store, 0, final_print, 0)

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_record_buffer.pd")
print("wrote test_record_buffer.pd")
