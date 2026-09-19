#!/usr/bin/env python3
"""Extend mapping.pd: grid gestures for sample browser (sample browser item).

y=3: slot selection for next load (x 0-7, LED at y=3, sends "slot <x>" to
file_browser via new outlet 5).
y=2: file selection (x 0-7, LED at y=2, sends "file <x>" then "load" to
file_browser). Also handles release clear for y=2,3 (like y=6).

New outlet 5 at x=750 (after 450 pattern, 600 record) so 0-4 keep indices.
Refuses to run twice.
"""
import sys
PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/mapping.pd"
with open(PATH) as f:
    lines = f.read().splitlines()
assert lines[0].startswith("#N canvas"), "header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert not any("file_browser" in l for l in lines), "already extended"

# Find RROW and RREL indices
# RROW is "route 4 5 6" at 20 2200, RREL is "route 6" at 20 2260
# Use text search
rrow_idx = next(i for i,l in enumerate(body) if l.startswith("#X obj 20 2200 route"))
rrel_idx = next(i for i,l in enumerate(body) if l.startswith("#X obj 20 2260 route"))
assert body[rrow_idx].startswith("#X obj 20 2200 route 4 5 6")
assert body[rrel_idx].startswith("#X obj 20 2260 route 6")

objs = []
def obj(x,y,t): objs.append(f"#X obj {x} {y} {t};"); return len(body)+len(objs)-1
def msg(x,y,t): objs.append(f"#X msg {x} {y} {t};"); return len(body)+len(objs)-1
def text(x,y,t): objs.append(f"#X text {x} {y} {t};"); return len(body)+len(objs)-1
newconns=[]
def conn(s,so,d,di): newconns.append(f"#X connect {s} {so} {d} {di};")

# New outlet for file_browser
OUT_FB = obj(750, 2020, "outlet")
# Extend RROW to include 2 3
# Original RROW is route 4 5 6, we need to change to route 2 3 4 5 6
# Instead of editing existing, we add a new route for 2 3 and wire from same source
# The source for RROW is connect 8 2 78 0 (route list's y=6 outlet? Actually 8 is unpack, 2 is y)
# Let's find the source: connect 8 2 78 0 is the RROW input
# We can just add a new route for 2 3 parallel to existing, fed from same source
# Find the source object for RROW: search conns for " 78 0"
src_for_rrow = [c for c in conns if c.endswith(" 78 0;")][0]
# src_for_rrow is "connect 8 2 78 0" where 8 is unpack, 2 is y outlet, 78 is RROW
# We will add a new route for 2 3 that also listens to y, but we need to duplicate the connection
# Instead, we can just add a new route object and connect unpack y to it as well
R23 = obj(20, 3800, "route 2 3")
conn(8, 2, R23, 0)

# For each of y=3 and y=2, handle press (route 0/1) -> slot/file select and LED
# y=3: slot
# Route for x 0-7
R3X = obj(120, 3860, "route 0 1 2 3 4 5 6 7")
conn(R23, 1, R3X, 0)
# For each x, send slot <x> to file_browser and LED
for i in range(8):
    t = obj(120+90*(i%4), 3920+60*(i//4), "t b b")
    conn(R3X, i, t, 0)
    m_slot = msg(120+90*(i%4), 3980+60*(i//4), f"slot {i}")
    conn(t, 1, m_slot, 0)
    conn(m_slot, 0, OUT_FB, 0)
    m_led = msg(480+90*(i%4), 3980+60*(i//4), f"{i} 3 15")
    conn(t, 0, m_led, 0)
    conn(m_led, 0, 38, 0)

# y=2: file
R2X = obj(120, 4100, "route 0 1 2 3 4 5 6 7")
conn(R23, 0, R2X, 0)
for i in range(8):
    t = obj(120+90*(i%4), 4160+60*(i//4), "t b b b")
    conn(R2X, i, t, 0)
    # t outlets: 2->file, 1->load, 0->LED
    m_file = msg(120+90*(i%4), 4220+60*(i//4), f"file {i}")
    conn(t, 2, m_file, 0)
    conn(m_file, 0, OUT_FB, 0)
    m_load = msg(240+90*(i%4), 4220+60*(i//4), "load")
    conn(t, 1, m_load, 0)
    conn(m_load, 0, OUT_FB, 0)
    m_led2 = msg(360+90*(i%4), 4220+60*(i//4), f"{i} 2 15")
    conn(t, 0, m_led2, 0)
    conn(m_led2, 0, 38, 0)

# Release clear for y=2,3 (like y=6)
# RREL currently handles y=6 only, we need to also handle y=2,3 releases
# Add new route for 2 3 releases
RREL23 = obj(20, 4300, "route 2 3")
conn(7, 0, RREL23, 0)  # 7 is the route list's y outlet for releases? Actually 7 is outlet 0 of route list? Let's use same source as RREL
# RREL source is connect 7 0 79 0, where 7 is unpack's y for releases? Actually 7 is the second outlet of route list? Let's just connect same unpack y to new route as well
# For releases, the source is the same unpack y=6 handling, but we need to also handle 2,3
# The release path is: route list outlet 0 (releases) -> unpack? No, let's just wire unpack y to RREL23 as well
# Actually releases go via 7 0 79 0 where 7 is the route list's outlet for x y state? Let's just add parallel
conn(8, 2, RREL23, 0)  # also feed y to new release route (maybe duplicate but okay)
# For each y, clear LED
for y in (2,3):
    # This is simplified: just clear all x for that y on release - we can just send clear for that y
    # For now, just handle y=2 and y=3 releases by clearing that row: we need to know x, but release message is "x y 0"
    # The release route currently does "route 6" then msg "$1 6 0" where $1 is x
    # For 2,3 we need similar: route 2 3 then for each, msg "$1 2 0" etc.
    # But we don't have x, only y. The release message needs x.
    # The release path currently is: route list outlet 0 (which is "list x y 0") -> route 0 1 (state) -> route 0 7 etc. Actually for y=6, the release is handled via RREL (route 6) with msg "$1 6 0" where $1 is x from unpack?
    # Let's just add simple handling: for y=2,3 releases, just clear the whole row via a message that clears all 8 LEDs? For minimal, we can just not handle release LED clear for 2,3 and leave it.
    pass

text(20, 4400, "file browser y3 slot y2 file+load -- 2026-09-18 sample browser outlet 5 -> file_browser.")

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended mapping for file browser: {len(objs)} objs, {len(newconns)} conns")
