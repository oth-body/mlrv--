#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/pattern_recorder.pd -- pattern
recorder, item 3 of the 1:1 mlrv recreation scope.

Sourced from trentgill/mlrv's own docs: "each one of the four available
pattern recorders can be set to a length of 1 to 32 bars. when armed,
the pattern recorder will wait until a button is pressed, then
immediately begin to record button presses until it reaches the end of
its recording buffer. then and there, the pattern will begin to
playback automatically... patterns may be silenced by simply pressing
the trigger button or deleted with a press-and-release gesture."

MVP scope, deliberately narrower than the original in one way: recording
length is taken directly in milliseconds via `length <ms>`, not bars --
converting bars to ms via clock.pd's tempo is a caller's job (this
abstraction doesn't depend on clock.pd at all, matching how clock.pd was
itself kept independent of file_poly.pd/mapping.pd). Overdub (hold +
play to merge new events into an existing pattern) is explicitly NOT
built here -- a real, separate design question, not guessed at.

Mechanism: [qlist], used the way Pd's own bundled example
(D13.additive.qlist.pd) uses it -- symbol-prefixed messages sent via a
named send/receive pair, NOT qlist's own numeric-list-output outlet.
Real, load-bearing probe finding, not assumed from the help text:
bare-numeric qlist entries (the OTHER documented mechanism -- "as soon
as a message starting with one or more numbers is encountered, the
numbers are output as a list") reproducibly failed to fire during auto
([bang]-triggered) playback in this Pd install across every variation
tried (add-built vs. file-read, single vs. multi-event, zero vs.
nonzero delay, DSP on vs. off) -- always jumping straight to the
done-bang with intermediate events silently skipped. Manual single-step
([next]) DID show them correctly, which is what made this worth
documenting rather than a wiring mistake. The symbol+receive mechanism
was verified working under auto-play with correct relative timing (a
second event added with delay 220 arrived exactly 220ms after the
first, via Pd's own [timer]).

qlist's delay-per-entry is RELATIVE TO THE PREVIOUS ENTRY, not an
absolute offset from playback start (confirmed against Pd's own bundled
qlist.txt) -- recording tracks "ms since the last recorded event" via a
[timer] reset after every add, not "ms since recording started".

Interface: `arm` (wait for first live event, clears any existing
pattern), a bare `list x y state` (a live grid event -- always passed
through to the outlet unconditionally, real-time performance is never
blocked by the recorder; captured into the pattern only while
armed/recording), `length <ms>` (recording duration before
auto-stop-and-loop, default 4000), `stop` (silence playback), `play`
(resume a stopped loop), `clear` (delete the pattern, stop everything).
Outlet 0: `list x y state` during playback. Outlet 1: the same live
pass-through events.

KNOWN LIMITATION, deliberate for this MVP: only one active instance is
safe at a time. qlist's send/receive addressing needs a per-instance
name (e.g. "gridevent1", "gridevent2") to avoid cross-talk between
multiple simultaneous recorders, which would need the abstraction's
creation arg concatenated into that name. [send gridevent\$1]/
[receive gridevent\$1] (object-box creation args) DO support this
concatenation correctly, but the qlist "add" entries themselves are
MESSAGE boxes, where \$N means "the Nth atom of whatever triggers this
box" (gotcha #1), not the abstraction's creation arg -- so the literal
text "gridevent" in an add-message can't pick up a per-instance suffix
the same way. The textbook fix ([symbol \$1], per Pd's own bundled
dollarsign2.pd reference) only emits the BARE creation arg as a runtime
atom, not a concatenation of it with other literal text -- verified this
does NOT work by probing [symbol somename\$1] directly (creation arg
syntax there does not support embedding \$N inside a longer literal the
way [send]/[receive] do; probed empirically, no output, no error).
Building real per-instance uniqueness needs either a string-concatenation
approach (not attempted here) or one abstraction FILE per instance
(defeats the point of an abstraction) -- deferred as a real, separate
problem rather than half-solved. Single shared "gridevent"
send/receive names are used instead; a second recorder instance in the
same patch would need this fixed first.

State machine (0=idle 1=armed 2=recording 3=playing 4=stopped),
transitions: arm->1; first live event while 1->2 (records with delay 0,
starts the auto-stop timer); auto-stop timer elapses while 2->3 (starts
qlist playback); qlist's own done-bang while 3->3 (auto-loop: rewind +
bang again); stop while (2,3)->4 (qlist rewind, i.e. stop without
clearing); play while 4->3 (resume); clear from any state->0 (qlist
clear).

Run from builders/: python3 build_pattern_recorder.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

p = Patch(w=900, h=800)

inlet = p.obj(20, 20, "inlet")
usage = p.text(120, 20,
    "pattern recorder (1:1 mlrv recreation item 3). inlet accepts: arm (wait for "
    "first live event \\, clears any existing pattern) \\, a bare list \\\"x y state\\\" "
    "(a live grid event -- always passed through unconditionally \\, captured only while "
    "armed/recording) \\, \\\"length <ms>\\\" (recording duration before auto-stop-and-loop "
    "\\, default 4000) \\, stop (silence playback) \\, play (resume a stopped loop) \\, "
    "clear (delete the pattern). outlet 0: \\\"x y state\\\" during playback. outlet 1: "
    "the same live pass-through events. OVERDUB IS NOT IMPLEMENTED -- a real \\, separate "
    "design question \\, not guessed at here. KNOWN LIMITATION: only ONE active instance "
    "is safe at a time -- uses a shared \\\"gridevent\\\" send/receive name \\, not "
    "per-instance \\, since qlist's add-entries are message boxes (\\$N = runtime atom \\, "
    "not creation arg \\, gotcha #1) and can't pick up a per-instance suffix the same way "
    "[send]/[receive]'s own creation args can. See this builder script's own module "
    "docstring for the full probe trail before attempting to fix this.")

route = p.obj(20, 80, "route arm length stop play clear")
p.connect(inlet, 0, route, 0)

state = p.obj(20, 550, "float 0")
length_store = p.obj(300, 130, "float 4000")
qlist = p.obj(20, 650, "qlist")
send_ev = p.obj(400, 130, "send gridevent")
recv_ev = p.obj(400, 170, "receive gridevent")
out_playback = p.obj(400, 750, "outlet")
out_live = p.obj(600, 750, "outlet")
p.connect(recv_ev, 0, out_playback, 0)

# --- arm: clear the pattern, set state=1 ---
arm_fan = p.obj(20, 120, "t b b")
p.connect(route, 0, arm_fan, 0)
m_clear_a = p.msg(60, 160, "clear")
m_armed = p.msg(20, 160, "1")
p.connect(arm_fan, 1, m_clear_a, 0)
p.connect(m_clear_a, 0, qlist, 0)
p.connect(arm_fan, 0, m_armed, 0)
p.connect(m_armed, 0, state, 1)

# --- length ---
p.connect(route, 1, length_store, 0)

# --- stop: qlist rewind (stop without clearing), state=4 ---
stop_fan = p.obj(20, 200, "t b b")
p.connect(route, 2, stop_fan, 0)
m_rewind_stop = p.msg(60, 240, "rewind")
m_stopped = p.msg(20, 240, "4")
p.connect(stop_fan, 1, m_rewind_stop, 0)
p.connect(m_rewind_stop, 0, qlist, 0)
p.connect(stop_fan, 0, m_stopped, 0)
p.connect(m_stopped, 0, state, 1)

# --- play: resume (bang qlist), state=3 ---
play_fan = p.obj(20, 280, "t b b")
p.connect(route, 3, play_fan, 0)
m_bang_play = p.msg(60, 320, "bang")
m_playing_resume = p.msg(20, 320, "3")
p.connect(play_fan, 1, m_bang_play, 0)
p.connect(m_bang_play, 0, qlist, 0)
p.connect(play_fan, 0, m_playing_resume, 0)
p.connect(m_playing_resume, 0, state, 1)

# --- clear: qlist clear, state=0 ---
clear_fan = p.obj(20, 360, "t b b")
p.connect(route, 4, clear_fan, 0)
m_clear_c = p.msg(60, 400, "clear")
m_idle = p.msg(20, 400, "0")
p.connect(clear_fan, 1, m_clear_c, 0)
p.connect(m_clear_c, 0, qlist, 0)
p.connect(clear_fan, 0, m_idle, 0)
p.connect(m_idle, 0, state, 1)

# --- live event: unconditional pass-through + gated recording capture ---
p.connect(route, 5, out_live, 0)  # reject outlet = bare "x y state" list, always passes through

live_unpack = p.obj(20, 440, "unpack f f f")
p.connect(route, 5, live_unpack, 0)

rec_pack = p.obj(200, 700, "pack f f f f")  # delay(hot,0) x(cold,1) y(cold,2) state(cold,3)
p.connect(live_unpack, 2, rec_pack, 3)  # state fires first (right-to-left)
p.connect(live_unpack, 1, rec_pack, 2)  # y fires second
x_tbf = p.obj(20, 480, "t b f")
p.connect(live_unpack, 0, x_tbf, 0)     # x fires last
p.connect(x_tbf, 1, rec_pack, 1)        # float (fires first of this t) -> cold-load x
# x_tbf outlet 0 (bang, fires last) triggers the state-check below

ev_timer = p.obj(600, 440, "timer")
rec_delay = p.obj(600, 480, "delay")
p.connect(length_store, 0, rec_delay, 1)  # keep the auto-stop interval current

p.connect(x_tbf, 0, state, 0)  # bang state's hot inlet: re-emits its CURRENT stored value
# NOTE: sending a bare bang to [float]'s hot inlet re-emits the current value (probe-verified
# earlier this session, same idiom as sample_voice~.pd's gain store) -- this does NOT reset it
# to 0, despite state's own creation arg being 0; only an explicit "0"/"1"/etc message resets it.

branch = p.obj(20, 590, "select 1 2")
p.connect(state, 0, branch, 0)

# branch A: armed -> first event -> start recording
m_recording = p.msg(20, 630, "2")
p.connect(branch, 0, m_recording, 0)
p.connect(m_recording, 0, state, 1)
p.connect(branch, 0, ev_timer, 0)      # reset timer (start counting from this first event)
p.connect(branch, 0, rec_delay, 0)     # arm the auto-stop countdown
zero_delay = p.msg(120, 630, "0")
p.connect(branch, 0, zero_delay, 0)
p.connect(zero_delay, 0, rec_pack, 0)  # hot inlet: emit (0, x, y, state)

# branch B: already recording -> read+reset the inter-event timer
readreset = p.obj(220, 630, "t b b")
p.connect(branch, 1, readreset, 0)
p.connect(readreset, 1, ev_timer, 1)   # report elapsed (fires first) -> feeds rec_pack below
p.connect(ev_timer, 0, rec_pack, 0)    # elapsed ms -> hot inlet: emit (elapsed, x, y, state)
p.connect(readreset, 0, ev_timer, 0)   # reset for the next gap (fires last)

add_msg = p.msg(200, 740, "add \\$1 gridevent \\$2 \\$3 \\$4")
p.connect(rec_pack, 0, add_msg, 0)
p.connect(add_msg, 0, qlist, 0)

# --- auto-stop: rec_delay elapses -> state=3, qlist rewind+bang ---
autostop_fan = p.obj(600, 520, "t b b")
p.connect(rec_delay, 0, autostop_fan, 0)
m_rewind_auto = p.msg(680, 560, "rewind")
m_bang_auto = p.msg(600, 560, "bang")
p.connect(autostop_fan, 1, m_rewind_auto, 0)
p.connect(m_rewind_auto, 0, qlist, 0)
p.connect(autostop_fan, 0, m_bang_auto, 0)
p.connect(m_bang_auto, 0, qlist, 0)
m_playing_auto = p.msg(760, 560, "3")
p.connect(rec_delay, 0, m_playing_auto, 0)
p.connect(m_playing_auto, 0, state, 1)

# --- loop: qlist done-bang -> if still playing, rewind+bang again ---
p.connect(qlist, 1, state, 0)  # bang state's hot inlet: re-emit current value
loop_check = p.obj(600, 600, "select 3")
p.connect(state, 0, loop_check, 0)
loop_fan = p.obj(600, 640, "t b b")
p.connect(loop_check, 0, loop_fan, 0)
p.connect(loop_fan, 1, m_rewind_auto, 0)
p.connect(loop_fan, 0, m_bang_auto, 0)

p.write("/home/aandi/repos/mlrv--/.claude/worktrees/pattern-recorder/mlrv-pd/abstractions/pattern_recorder.pd")
print("wrote pattern_recorder.pd")
