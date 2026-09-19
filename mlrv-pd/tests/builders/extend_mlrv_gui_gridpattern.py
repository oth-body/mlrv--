#!/usr/bin/env python3
"""Extend mlrv-gui.pd: hear mapping.pd's new grid-gesture outlets (grid
gestures follow-up, 2026-09-18): outlet 3 (pattern transport buttons) ->
pattern_recorder inlet, outlet 4 (record button) -> record_buffer~ inlet.
Two connects, no new objects. Refuses to run twice.
"""

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/mlrv-gui.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

body = [l for l in lines[1:] if not l.startswith("#X connect")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]

def idx_of(text):
    m = [i for i, l in enumerate(body) if l == text]
    assert len(m) == 1, f"not unique/found: {text}"
    return m[0]

MAPPING = idx_of("#X obj 300 200 mapping;")
PREC = idx_of("#X obj 900 80 pattern_recorder;")
RBUF = next(i for i, l in enumerate(body) if l.startswith("#X obj 900 200 record_buffer~"))
for s, so, d in ((MAPPING, 3, PREC), (MAPPING, 4, RBUF)):
    assert not any(c.startswith(f"#X connect {s} {so} ") for c in conns), \
        f"outlet taken: {s} {so}"
newconns = [f"#X connect {MAPPING} 3 {PREC} 0;",
            f"#X connect {MAPPING} 4 {RBUF} 1;"]

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + conns + newconns) + "\n")
print("wired mapping outlets 3/4 to pattern/record")
