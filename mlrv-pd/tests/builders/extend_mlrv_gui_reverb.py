#!/usr/bin/env python3
"""Extend mlrv-gui.pd: add the reverb effect alongside the existing
delay_fx~, same as extend_mlrv_reverb.py does for mlrv.pd -- see that
script's docstring for the full reasoning (real outlet~ per effect,
summed via [+~] into the one real [send~ fxin], not a bus-based send~
fxin per effect, which would collide per gotcha #31).

Purely additive -- no existing object is touched or renumbered.
Refuses to run twice (checks for reverb_fx~ already present).
"""
PATH = "/home/aandi/repos/mlrv--/mlrv-pd/mlrv-gui.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

header = lines[0]
body = [l for l in lines[1:] if not l.startswith("#X connect")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]

if any("reverb_fx~" in l for l in body):
    print("skip: reverb_fx~ already wired")
    raise SystemExit(0)

delay_idx = body.index("#X obj 600 320 delay_fx~;")

new_objs = [
    "#X obj 720 320 reverb_fx~;",
    "#X obj 600 360 +~;",
    "#X obj 600 400 send~ fxin;",
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
