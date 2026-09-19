#!/usr/bin/env python3
"""Extend file_poly.pd: per-voice audio outlets (mixer-wiring item).

Each of the 4 sample_voice~ instances exposes post-envelope audio on its
outlet 0; today those feed ONLY the internal +~ sum chain (v1+v2, v3+v4).
This appends 4 outlet~ (x=300/420/540/660, all right of the existing
outlets, so outlets 0/1 keep indices per gotcha 10) and fans each voice
outlet out to both the untouched sum chain and its own outlet (signal
fan-out is free -- no ordering or store concerns, unlike every control
path in this file's history).

The internal sum and outlet 0 stay exactly as-is: every existing suite
captures through them and must pass unmodified afterward.

Refuses to run twice.
"""
import sys

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/file_poly.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

assert lines[0].startswith("#N canvas"), "unexpected header"
body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]
assert len(body) + len(conns) == len(lines) - 1, "unexpected line types present"
assert len(body) == 243, f"body moved: {len(body)}"
assert len(conns) == 354, f"connects moved: {len(conns)}"
assert not any("voice outlet" in l for l in lines), "already extended -- refusing to double-append"

for i, s in enumerate(["mlrv-sample-0", "mlrv-sample-1", "mlrv-sample-2", "mlrv-sample-3"]):
    assert body[75 + i] == f"#X obj 460 {760 + 60 * i} sample_voice~ {s};", f"voice {i} moved"
assert body[82] == "#X obj 20 50 outlet~;", "sum outlet moved"
assert body[21] == "#X obj 140 660 outlet;", "info outlet moved"
for a, b, c, d in ((75, 0, 79, 0), (76, 0, 79, 1), (77, 0, 80, 0), (78, 0, 80, 1)):
    assert f"#X connect {a} {b} {c} {d};" in conns, f"sum voice connect missing: {a}"

objs = []
def obj(x, y, text):
    objs.append(f"#X obj {x} {y} {text};")
    return len(body) + len(objs) - 1

def text(x, y, text):
    objs.append(f"#X text {x} {y} {text};")
    return len(body) + len(objs) - 1

objs.append("#X text 20 3400 per-voice audio outlets 2-5 (2026-09-18 \\, mixer-wiring item) -- 4 outlet~ fan-out from file_poly voices to mixer.pd.")
OV = [obj(200 + 60 * i, 60, "outlet~") for i in range(4)]

newconns = []
for i, v in enumerate((75, 76, 77, 78)):
    newconns.append(f"#X connect {v} 0 {OV[i]} 0;")



with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"extended: {len(objs)} objects, {len(newconns)} new connects")
