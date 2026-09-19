#!/usr/bin/env python3
"""Extend mlrv.pd: add the reverb effect alongside the existing
delay_fx~ (full-codebase gap analysis item 2), and correct delay_fx~'s
now-outlet~-based output (extend_mlrv_delay.py placed it as a purely
bus-based object with no connections -- an interface it no longer has,
see build_delay_fx.py's docstring for why: two effects each with their
own internal send~ fxin would collide, gotcha #31).

Purely additive (unlike extend_mlrv_delay.py, which had to remove the
old stub and renumber): appends reverb_fx~, a [+~] summer, and the one
real [send~ fxin], then connects delay_fx~'s and reverb_fx~'s outlet~s
into the summer and the summer into send~ fxin. No existing object is
touched or renumbered -- gotcha #7's append-only escape hatch.

Refuses to run twice (checks for reverb_fx~ already present).
"""
PATH = "/home/aandi/repos/mlrv--/mlrv-pd/mlrv.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

header = lines[0]
body = [l for l in lines[1:] if not l.startswith("#X connect")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]

if any("reverb_fx~" in l for l in body):
    print("skip: reverb_fx~ already wired")
    raise SystemExit(0)

delay_idx = body.index("#X obj 460 320 delay_fx~;")

new_objs = [
    "#X obj 600 320 reverb_fx~;",
    "#X obj 460 360 +~;",
    "#X obj 460 400 send~ fxin;",
]
reverb_idx = len(body)
sum_idx = reverb_idx + 1
send_idx = reverb_idx + 2
body = body + new_objs

new_conns = [
    f"#X connect {delay_idx} 0 {sum_idx} 0;",
    f"#X connect {reverb_idx} 0 {sum_idx} 1;",
    f"#X connect {sum_idx} 0 {send_idx} 0;",
]

out_lines = [header] + body + conns + new_conns
with open(PATH, "w") as f:
    f.write("\n".join(out_lines) + "\n")
print(f"wired reverb_fx~ (index {reverb_idx}), summed with delay_fx~ ({delay_idx}) "
      f"into +~ ({sum_idx}) -> send~ fxin ({send_idx})")
