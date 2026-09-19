#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/mapper.pd -- the MIDI/OSC/keyboard
mapping engine (1:1 mlrv recreation, item 5 mapping GUI, increment 1:
the binding core; widgets/adapters are increment 2).

Model: every mappable engine endpoint is a PARAM (flat symbol, e.g.
`tempo`, `vgain1`). External controls arrive normalized as
`ctl <class> <id> <val01>` (class 0=MIDI 1=OSC 2=KEY; adapters in
increment 2 produce this; increment 1 tests send it directly).
`learn <sym>` arms a param; the next ctl BINDS (stealing the source from
any previous owner); otherwise ctl DISPATCHES through the binding with
per-param min/max scaling. `min/max/clear <sym> [...]` edit and remove
bindings. Outlet 0 = engine messages, outlet 1 = reports
(`learning <idx>`, `bound <idx> <srcid>`).

Key design points (all established codebase idioms, no new probes needed):
- src identity packs into one int: srcid = class*128+id. Two float tables:
  fwd[paramidx] = srcid+1, rev[srcid] = paramidx+1 (0 = unbound in both,
  which is also table zero-init -- same convention as mlrv-fpgroup).
- The ctl unpack phase ONLY stores (val into the route-pack's cold inlet,
  id/class into the srcid expr, srcid silently into its store's RIGHT
  inlet per gotcha 23). A master `[t b b]` then bangs the armed store:
  unarmed -> re-emit srcid down the dispatch path; armed -> bind path.
  Nothing downstream can fire on a store-write, by construction.
- Dispatch packs [idx val] (idx hot-last per gotcha 15 -- unpack fires
  right-to-left so val lands cold first) into `[route 0..N-1]`; unbound
  (idx -1) falls out the reject outlet, dropped silently.
- Per-param scaling rereads editable min/max TABLES per trigger (const idx
  msg fans to both tabreads, value arrives hot-last via `[t b b b]`).
- `[t b f]` is used deliberately for bang+float in the admin path with
  full awareness of gotcha 25 (bang fires first by design here).
- min/max admin reuses one sym-route per verb (learn/min/max/clear each
  get their own, since learn carries a bare symbol while min/max carry
  a value -- sharing one route would mix bang and float remainders on
  the same outlets).

PARAMS drives everything; increment 1 covers all four kinds (cont, dint,
dsym, trig) with 7 params so increment 2 is a table extension, not a
rewrite. Refuses to run twice (mapper.pd must not exist).
Run from builders/: python3 build_mapper.py
"""
import os
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
from mapper_params import PARAMS

OUT = "/home/aandi/repos/mlrv--/mlrv-pd/abstractions/mapper.pd"
assert not os.path.exists(OUT), "mapper.pd exists -- refusing to double-build"

# sym, kind, min, max, format. cont/dint: template with $1. dsym: two full
# messages (int 0/1 selects). trig: one fixed message fired on any ctl.
# NOTE: pat_*/rec_* transports stay OUT of the shared GUI demux (their bare
# `play`/`stop` collide with file_poly's arg-carrying `play`/`stop` on a
# shared bus) -- they live in mapper for OSC/MIDI users and get DIRECT
# widget->engine buttons in the GUI. vol/send stay message-only until the
# file_poly->mixer wiring TODO lands (same as mlrv.pd).
# PARAMS itself lives in mapper_params.py (shared with build_mlrv_gui.py).
N = len(PARAMS)
SYMS = [p["sym"] for p in PARAMS]
NREV = 3 * 128

p = Patch(w=1400, h=2200)

inlets = p.obj(20, 20, "inlet")
r0 = p.obj(20, 70, "route learn min max clear ctl mini maxi")
p.connect(inlets, 0, r0, 0)

symlist = " ".join(SYMS)
r_learn = p.obj(20, 130, f"route {symlist}")
r_min = p.obj(300, 130, f"route {symlist}")
r_max = p.obj(580, 130, f"route {symlist}")
r_clear = p.obj(860, 130, f"route {symlist}")
p.connect(r0, 0, r_learn, 0)
p.connect(r0, 1, r_min, 0)
p.connect(r0, 2, r_max, 0)
p.connect(r0, 3, r_clear, 0)

# --- tables + loadbang seeding of min/max defaults ---
t_fwd = p.obj(1140, 20, f"table mlrv-mapfwd {N}")
t_rev = p.obj(1140, 70, f"table mlrv-maprev {NREV}")
t_mins = p.obj(1140, 120, f"table mlrv-mapmin {N}")
t_maxs = p.obj(1140, 170, f"table mlrv-mapmax {N}")
tw_fwd = p.obj(1290, 20, "tabwrite mlrv-mapfwd")
tw_rev = p.obj(1290, 70, "tabwrite mlrv-maprev")
tw_min = p.obj(1290, 120, "tabwrite mlrv-mapmin")
tw_max = p.obj(1290, 170, "tabwrite mlrv-mapmax")
lb = p.obj(1140, 230, "loadbang")
seedt = p.obj(1140, 270, "t " + " ".join(["b"] * (2 * N)))
p.connect(lb, 0, seedt, 0)
for i, pr in enumerate(PARAMS):
    m1 = p.msg(900 + 100 * (i % 2), 320 + 80 * (i // 2), f"{pr['min']} {i}")
    m2 = p.msg(900 + 100 * (i % 2), 360 + 80 * (i // 2), f"{pr['max']} {i}")
    p.connect(seedt, 2 * i, m1, 0)
    p.connect(m1, 0, tw_min, 0)
    p.connect(seedt, 2 * i + 1, m2, 0)
    p.connect(m2, 0, tw_max, 0)

# --- ctl path: unpack stores only, master trigger decides ---
unp = p.obj(20, 220, "unpack f f f")
p.connect(r0, 4, unp, 0)
clip = p.obj(20, 280, "clip 0 1")
packIV = p.obj(20, 340, "pack f f")
p.connect(unp, 2, clip, 0)
p.connect(clip, 0, packIV, 1)
esrc = p.obj(200, 280, "expr \\$f1*128+\\$f2")
p.connect(unp, 1, esrc, 1)
srcstore = p.obj(200, 340, "float 0")
srcstoreB = p.obj(330, 340, "float 0")
p.connect(esrc, 0, srcstore, 1)
p.connect(esrc, 0, srcstoreB, 1)
master = p.obj(20, 400, "t b b")
Ford = p.obj(110, 400, "t f f")
p.connect(unp, 0, Ford, 0)
p.connect(Ford, 1, esrc, 0)
p.connect(Ford, 0, master, 0)
armed = p.obj(200, 400, "float -1")
p.connect(master, 0, armed, 0)
selarmed = p.obj(200, 460, "sel -1")
p.connect(armed, 0, selarmed, 0)

dispatch = p.obj(20, 520, f"route {' '.join(str(i) for i in range(N))}")
rd_rev = p.obj(200, 520, "tabread mlrv-maprev")
minus1 = p.obj(200, 580, "- 1")
p.connect(selarmed, 0, srcstore, 0)
p.connect(srcstore, 0, rd_rev, 0)
p.connect(rd_rev, 0, minus1, 0)
p.connect(minus1, 0, packIV, 0)
p.connect(packIV, 0, dispatch, 0)

out_dispatch = p.obj(20, 2130, "outlet")
out_report = p.obj(200, 2130, "outlet")
pr_learning = p.obj(400, 2130, "print learning")
pr_bound = p.obj(600, 2130, "print bound")

# --- learn: sym-route outlet i -> const idx -> armed + report + tag ---
for i in range(N):
    ci = p.msg(60 + 90 * i, 190, str(i))
    tl = p.obj(60 + 90 * i, 220, "t f f")
    p.connect(r_learn, i, ci, 0)
    p.connect(ci, 0, tl, 0)
    p.connect(tl, 1, armed, 1)
    p.connect(tl, 0, pr_learning, 0)
    p.connect(tl, 0, out_report, 0)
    lt = p.msg(60 + 90 * i, 250, "learning \\$1")
    p.connect(tl, 0, lt, 0)
    p.connect(lt, 0, out_report, 0)

# --- min/max admin: outlet i -> val-carrying msg -> tabwrite ---
for i in range(N):
    m1 = p.msg(300 + 90 * (i % 4), 190 + 60 * (i // 4), f"\\$1 {i}")
    m2 = p.msg(580 + 90 * (i % 4), 190 + 60 * (i // 4), f"\\$1 {i}")
    p.connect(r_min, i, m1, 0)
    p.connect(m1, 0, tw_min, 0)
    p.connect(r_max, i, m2, 0)
    p.connect(m2, 0, tw_max, 0)

# --- bind path (armed ctl): stash, write fwd+rev, reset, report ---
# NOTE (gotcha 25, third occurrence in this codebase): the stash re-emits
# below fan out to exactly one HOT inlet each. An earlier draft shared one
# idxstash across packF/plus1r/packRep's hot inlets, so every re-emit fired
# all three (triple prints, triple idempotent rewrites). Dedicated stash
# per consumer; srcstore stays shared only because every one of ITS bind-
# phase consumers terminates cold (plus1f-hot re-emits into packF-cold).
idxstashF = p.obj(400, 460, "float 0")
idxstashR = p.obj(520, 460, "float 0")
idxstashP = p.obj(640, 460, "float 0")
bindseq = p.obj(400, 520, "t b b b b b b")
plus1f = p.obj(400, 580, "+ 1")
packF = p.obj(400, 640, "pack f f")
plus1r = p.obj(620, 580, "+ 1")
packR = p.obj(620, 640, "pack f f")
packRep = p.obj(840, 640, "pack f f")
rstmsg = p.msg(840, 700, "-1")
tff = p.obj(400, 400, "t f f")
p.connect(selarmed, 1, tff, 0)
p.connect(tff, 1, idxstashF, 1)
p.connect(tff, 1, idxstashR, 1)
p.connect(tff, 1, idxstashP, 1)
p.connect(tff, 0, bindseq, 0)
# tabwrite wants [value index]: packF must emit [src+1 idx], so idx goes
# COLD (out5, first) and src+1 goes HOT (out4, second). Getting this
# backwards writes value=idx at index=src+1 -- out of range, silent no-op.
p.connect(bindseq, 5, idxstashF, 0)
p.connect(idxstashF, 0, packF, 1)
p.connect(bindseq, 4, srcstoreB, 0)
p.connect(srcstoreB, 0, plus1f, 0)
p.connect(plus1f, 0, packF, 0)
p.connect(packF, 0, tw_fwd, 0)
p.connect(bindseq, 3, srcstoreB, 0)
p.connect(srcstoreB, 0, packR, 1)
p.connect(bindseq, 2, idxstashR, 0)
p.connect(idxstashR, 0, plus1r, 0)
p.connect(plus1r, 0, packR, 0)
p.connect(packR, 0, tw_rev, 0)
p.connect(bindseq, 1, srcstoreB, 0)
p.connect(srcstoreB, 0, packRep, 1)
p.connect(bindseq, 0, idxstashP, 0)
p.connect(idxstashP, 0, packRep, 0)
tllB = p.obj(840, 670, "t l l")
p.connect(packRep, 0, tllB, 0)
p.connect(tllB, 1, pr_bound, 0)
p.connect(tllB, 0, out_report, 0)
bt = p.msg(840, 700 - 30, "bound \\$1 \\$2")
p.connect(packRep, 0, bt, 0)
p.connect(bt, 0, out_report, 0)
p.connect(packRep, 0, rstmsg, 0)
p.connect(rstmsg, 0, armed, 1)

# --- mini/maxi admin: numeric-index twin of min/max (for the GUI's shared
# editor row, which thinks in indices, not symbols). `mini <idx> <v>` scaling
# uses the same value-first tabwrite idiom throughout this codebase.
valAdmin = p.obj(1140, 400, "float 0")
for verb, tbl in (("mini", tw_min), ("maxi", tw_max)):
    au = p.obj(1140, 460, "unpack f f")
    at = p.obj(1140, 520, "t b f")
    ap = p.obj(1140, 580, "pack f f")
    am = p.msg(1140, 640, "\\$2 \\$1")
    if verb == "mini":
        p.connect(r0, 5, au, 0)
    else:
        p.connect(r0, 6, au, 0)
    p.connect(au, 1, valAdmin, 1)
    p.connect(au, 0, at, 0)
    p.connect(at, 1, valAdmin, 0)
    p.connect(valAdmin, 0, ap, 1)
    p.connect(at, 0, ap, 0)
    p.connect(ap, 0, am, 0)
    p.connect(am, 0, tbl, 0)

# --- clear path: sym-route outlet i -> const idx -> shared chain ---
rd_fwd = p.obj(860, 400, "tabread mlrv-mapfwd")
cminus = p.obj(860, 460, "- 1")
ctff = p.obj(860, 340, "t f f")
cmsgR = p.msg(860, 520, "0 \\$1")
cmsgF = p.msg(980, 520, "0 \\$1")
for i in range(N):
    ci = p.msg(860 + 90 * (i % 4), 190 + 60 * (i // 4), str(i))
    p.connect(r_clear, i, ci, 0)
    p.connect(ci, 0, ctff, 0)
p.connect(ctff, 1, rd_fwd, 0)
p.connect(rd_fwd, 0, cminus, 0)
p.connect(cminus, 0, cmsgR, 0)
p.connect(cmsgR, 0, tw_rev, 0)
p.connect(ctff, 0, cmsgF, 0)
p.connect(cmsgF, 0, tw_fwd, 0)

# --- per-param dispatch chains ---
for i, pr in enumerate(PARAMS):
    y = 640 + 140 * i
    if pr["kind"] in ("cont", "dint"):
        # NOTE: [t f f f], not [t b b b] -- gotcha 25: a b-type outlet drops
        # the value, and outlet 0 must deliver val itself (hot) to expr after
        # outlet 2's const/tabread subtree pre-loads the cold inlets.
        tb = p.obj(20, y, "t f f f")
        p.connect(dispatch, i, tb, 0)
        ci = p.msg(110, y, str(i))
        p.connect(tb, 2, ci, 0)
        trmin = p.obj(200, y, "tabread mlrv-mapmin")
        trmax = p.obj(320, y, "tabread mlrv-mapmax")
        p.connect(ci, 0, trmin, 0)
        p.connect(ci, 0, trmax, 0)
        if pr["kind"] == "cont":
            ex = p.obj(440, y, "expr \\$f1*(\\$f2-\\$f3)+\\$f3")
        else:
            ex = p.obj(440, y, "expr int(\\$f1*(\\$f2-\\$f3)+\\$f3)")
        p.connect(trmax, 0, ex, 1)
        p.connect(trmin, 0, ex, 2)
        p.connect(tb, 0, ex, 0)
        fm = p.msg(700, y, pr["fmt"])
        p.connect(ex, 0, fm, 0)
        p.connect(fm, 0, out_dispatch, 0)
    elif pr["kind"] == "dsym":
        tb = p.obj(20, y, "t f f f")
        p.connect(dispatch, i, tb, 0)
        ci = p.msg(110, y, str(i))
        p.connect(tb, 2, ci, 0)
        trmin = p.obj(200, y, "tabread mlrv-mapmin")
        trmax = p.obj(320, y, "tabread mlrv-mapmax")
        p.connect(ci, 0, trmin, 0)
        p.connect(ci, 0, trmax, 0)
        ex = p.obj(440, y, "expr int(\\$f1*(\\$f2-\\$f3)+\\$f3)")
        p.connect(trmax, 0, ex, 1)
        p.connect(trmin, 0, ex, 2)
        p.connect(tb, 0, ex, 0)
        rs = p.obj(700, y, "route 0 1")
        p.connect(ex, 0, rs, 0)
        m0 = p.msg(790, y, pr["m0"])
        m1 = p.msg(920, y, pr["m1"])
        p.connect(rs, 0, m0, 0)
        p.connect(rs, 1, m1, 0)
        p.connect(m0, 0, out_dispatch, 0)
        p.connect(m1, 0, out_dispatch, 0)
    elif pr["kind"] == "trig":
        tb = p.obj(20, y, "t b")
        p.connect(dispatch, i, tb, 0)
        fm = p.msg(200, y, pr["fmt"])
        p.connect(tb, 0, fm, 0)
        p.connect(fm, 0, out_dispatch, 0)

p.write(OUT)
print(f"wrote mapper.pd: {N} params")
