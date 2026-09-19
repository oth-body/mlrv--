#!/usr/bin/env python3
"""Builders for the three mapper `ctl` source adapters (1:1 mlrv recreation,
item 5 mapping GUI, increment 2). Each emits `ctl <class> <id> <val01>` for
mapper.pd's inlet 0:

- osc_ctl.pd [port] (default 9000): `[udpreceive]` + `[oscparse]` listening
  for `/mlrv/ctl <id> <val01>`. Headless-verifiable over real UDP (see
  run_mlrv_gui_test.sh, which sends bytes from stdlib python).
- midi_ctl.pd: `[ctlin]` (all channels) -> CC number + value/127. Loads
  clean headless; live MIDI needs hardware (same pre-hardware status
  serialosc.pd had for its first turns -- labeled, not hidden).
- key_ctl.pd: `[key]`/`[keyup]` -> `ctl 2 <keycode> 1/0`. Same headless note
  as MIDI (`key` needs a GUI window focus to produce anything live).

Run from builders/: python3 build_ctl_adapters.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

PRE = "/home/aandi/repos/mlrv--/mlrv-pd/abstractions/"

# --- osc_ctl.pd ---
p = Patch(w=800, h=400)
ur = p.obj(20, 20, "netreceive -u -b \\$1")
op = p.obj(20, 70, "oscparse")
p.connect(ur, 0, op, 0)
r0 = p.obj(20, 120, "route list")
p.connect(op, 0, r0, 0)
r1 = p.obj(20, 170, "route mlrv")
p.connect(r0, 0, r1, 0)
r2 = p.obj(20, 220, "route ctl")
p.connect(r1, 0, r2, 0)
unp = p.obj(20, 270, "unpack f f")
p.connect(r2, 0, unp, 0)
pk = p.obj(20, 300, "pack f f")
p.connect(unp, 1, pk, 1)
p.connect(unp, 0, pk, 0)
fmt = p.msg(20, 330, "ctl 1 \\$1 \\$2")
p.connect(pk, 0, fmt, 0)
out = p.obj(20, 365, "outlet")
p.connect(fmt, 0, out, 0)
p.text(300, 20, "OSC -> ctl adapter. listens on creation-arg port ( vanilla has no [udpreceive] -- probed \\, so [netreceive -u -b] like serialosc.pd) for /mlrv/ctl <id 0-127> <val 0-1>. instantiate [osc_ctl 9000]. crab: oscparse splits the address on / and prefixes list (gotcha 3) \\, hence the nested route chain.")
p.write(PRE + "osc_ctl.pd")

# --- midi_ctl.pd ---
p = Patch(w=800, h=300)
ctlin = p.obj(20, 20, "ctlin")
div = p.obj(20, 70, "/ 127")
p.connect(ctlin, 0, div, 0)
pack = p.obj(20, 120, "pack f f")
p.connect(ctlin, 1, pack, 1)
p.connect(div, 0, pack, 0)
fmt = p.msg(20, 170, "ctl 0 \\$2 \\$1")
p.connect(pack, 0, fmt, 0)
out = p.obj(20, 220, "outlet")
p.connect(fmt, 0, out, 0)
p.text(300, 20, "MIDI CC -> ctl adapter. ctlin outlets: value (hot) then cc# -- right-to-left puts cc# cold-first \\, value hot-last (gotcha 15) -- value normalized to 0-1. live MIDI needs hardware -- loads clean without.")
p.write(PRE + "midi_ctl.pd")

# --- key_ctl.pd ---
p = Patch(w=800, h=300)
key = p.obj(20, 20, "key")
f1 = p.msg(20, 70, "ctl 2 \\$1 1")
p.connect(key, 0, f1, 0)
keyu = p.obj(300, 20, "keyup")
f0 = p.msg(300, 70, "ctl 2 \\$1 0")
p.connect(keyu, 0, f0, 0)
out = p.obj(20, 130, "outlet")
p.connect(f1, 0, out, 0)
p.connect(f0, 0, out, 0)
p.text(20, 180, "computer-keyboard -> ctl adapter. keycode becomes the ctl id (class 2: srcid = 256+code -- codes above 127 exceed mapper's 384-cell reverse table and will not bind -- letters/digits fit). needs Pd GUI focus live -- silent headless.")
p.write(PRE + "key_ctl.pd")

print("wrote osc_ctl.pd midi_ctl.pd key_ctl.pd")
