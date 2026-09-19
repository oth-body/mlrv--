#!/usr/bin/env python3
"""Fix mapping.pd gestures: distribute slot x into the stash cold inlets
(grid-gesture follow-up).

Root cause, caught by a live probe (not inspection): the slot value rode
TFA/TFA2's outlet 0 straight into `[t b b]`/`[t b b b]`, whose b-type
outlets drop it (gotcha 25) -- then fanned the resulting bangs into the
stash LEFT inlets (re-emit), so every stash held its 0-init and every LED
/ group message / store used slot 0. The design doc said "x -> xS-R"
but the builder wired "bang -> xS-L".

Fix: interpose `[t f f]` (XD/XD2): outlet 1 (x, first) fans to the stash
RIGHT inlets (silent); outlet 0 (second) bangs the re-emit trigger.
Refuses to run twice.
"""

PATH = "/home/aandi/repos/mlrv--/mlrv-pd/patchers/mapping.pd"

with open(PATH) as f:
    lines = f.read().splitlines()

body = [l for l in lines[1:] if l.startswith("#X obj") or l.startswith("#X msg") or l.startswith("#X text")]
conns = [l for l in lines[1:] if l.startswith("#X connect")]

def idx_of(text):
    matches = [i for i, l in enumerate(body) if l == text]
    assert len(matches) == 1, f"not unique/found: {text}"
    return matches[0]

TFA = idx_of("#X obj 120 2860 t f f;") if any("2860" in l for l in body) else None
# locate robustly by topology instead: TFA feeds tabread mlrv-mslave
TRD = idx_of("#X obj 120 2920 tabread mlrv-mslave;") if False else None

# robust: find `t f f` whose outlet1 goes to a `tabread mlrv-mslave`
tffs = [i for i, l in enumerate(body) if l.endswith("t f f;")]
TFA = TFA2 = TXT = TXA = None
XS = XL = XS2 = XL2 = XG = None
for i in tffs:
    outs = sorted(c for c in conns if c.startswith(f"#X connect {i} 1 "))
    if len(outs) == 1 and "tabread mlrv-mslave" in body[int(outs[0].split()[4])]:
        TFA = i
    outs0 = sorted(c for c in conns if c.startswith(f"#X connect {i} 0 "))
    # TFA2's outlet1 goes to tabread mlrv-mgroup
    if len(outs) == 1 and "tabread mlrv-mgroup" in body[int(outs[0].split()[4])]:
        TFA2 = i
assert TFA is not None and TFA2 is not None, "TFA/TFA2 not found"

# TXT: `t b b` fed by TFA outlet 0; TXA: `t b b b` fed by TFA2 outlet 0
def dst_of(s, so):
    return [int(c.split()[4]) for c in conns if c.startswith(f"#X connect {s} {so} ")]
TXT = dst_of(TFA, 0)
TXA = dst_of(TFA2, 0)
assert len(TXT) == 1 and body[TXT[0]].endswith("t b b;"), f"TXT: {TXT}"
assert len(TXA) == 1 and body[TXA[0]].endswith("t b b b;"), f"TXA: {TXA}"
TXT, TXA = TXT[0], TXA[0]
assert not any("t f f;" in l and "2260" in l for l in body), "already fixed?"
# stash floats: find by their (currently wrong) feeders TXT-outlet1 / TXA-outlets
XS = dst_of(TXT, 1)
assert len(XS) == 1 and body[XS[0]].startswith("#X obj") and "float 0" in body[XS[0]], f"XS: {XS}"
XS = XS[0]
XL = dst_of(TXT, 0)
assert len(XL) == 1 and "float 0" in body[XL[0]], f"XL: {XL}"
XL = XL[0]
XS2 = dst_of(TXA, 2)
XL2 = dst_of(TXA, 1)
XG = dst_of(TXA, 0)
for name, v in (("XS2", XS2), ("XL2", XL2), ("XG", XG)):
    assert len(v) == 1 and "float 0" in body[v[0]], f"{name}: {v}"
XS2, XL2, XG = XS2[0], XL2[0], XG[0]

OLD1 = f"#X connect {TFA} 0 {TXT} 0;"
OLD2 = f"#X connect {TFA2} 0 {TXA} 0;"
assert conns.count(OLD1) == 1 and conns.count(OLD2) == 1, "expected connects missing"
conns.remove(OLD1)
conns.remove(OLD2)

objs = []
XD = len(body) + len(objs)
objs.append("#X obj 420 2980 t f f;")
XD2 = len(body) + len(objs)
objs.append("#X obj 700 3340 t f f;")

newconns = [
    f"#X connect {TFA} 0 {XD} 0;",
    f"#X connect {XD} 1 {XS} 1;",
    f"#X connect {XD} 1 {XL} 1;",
    f"#X connect {XD} 0 {TXT} 0;",
    f"#X connect {TFA2} 0 {XD2} 0;",
    f"#X connect {XD2} 1 {XS2} 1;",
    f"#X connect {XD2} 1 {XL2} 1;",
    f"#X connect {XD2} 1 {XG} 1;",
    f"#X connect {XD2} 0 {TXA} 0;",
]

with open(PATH, "w") as f:
    f.write("\n".join([lines[0]] + body + objs + conns + newconns) + "\n")
print(f"fixed: XD={XD} XD2={XD2}")
