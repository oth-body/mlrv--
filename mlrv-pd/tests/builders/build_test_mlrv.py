#!/usr/bin/env python3
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
from mlrv_core import build_core

p = Patch(w=1200, h=700)

HEADER = p.text(
    20, 20,
    "test_mlrv.pd -- automated end-to-end regression for mlrv.pd. Uses "
    "the SAME core wiring (mlrv_core.build_core) as the real mlrv.pd\\, "
    "so this stays honest about what it is actually testing rather than "
    "a hand-copied approximation that could silently drift. Runs "
    "against tests/fake_serialosc.py (a fake daemon + fake grid device\\, "
    "no real hardware needed) with its simulated key event pointed at "
    "the trigger row for slot 0. Captures master\\'s real audio output "
    "via tabwrite~ and the LED command mapping.pd sends back\\, so this "
    "verifies the whole chain (key press -> mapping -> file_poly -> "
    "master -> real signal\\, AND file_poly -> mapping -> grid -> LED) "
    "without anyone needing to listen to anything. See "
    "run_mlrv_test.sh for the pass/fail assertions."
)

core = build_core(p)
SERIALOSC, GRID, FILE_POLY, MAPPING, MIXER, MASTER = (
    core["SERIALOSC"], core["GRID"], core["FILE_POLY"], core["MAPPING"], core["MIXER"], core["MASTER"]
)

N = 4410
CAP_TABLE = p.obj(150, 600, f"table mlrv-e2e-cap {N}")

# audio capture tap (replaces dac~ -- no real audio hardware needed)
TAPWRITE = p.obj(600, 420, "tabwrite~ mlrv-e2e-cap")
p.connect(MASTER, 0, TAPWRITE, 0)

# LED capture tap: whatever mapping.pd sends grid.pd for the triggered
# cell should be a bright ("on") level -- print it so the check script
# can grep the log rather than needing a signal capture for this part.
LED_PRINT = p.obj(20, 320, "print mlrv_e2e_led")
p.connect(GRID, 0, LED_PRINT, 0)

# --- bootstrap: dsp on, gain, load one known fixture into slot 0, rescan ---
LB = p.obj(20, 400, "loadbang")
DSP_ON = p.msg(20, 440, "\\; pd dsp 1")
GAIN = p.msg(150, 440, "0.8")
LOAD0 = p.msg(280, 440, "load 0 /tmp/mlrv_e2e_src.wav")
RESCAN = p.obj(410, 440, "delay 200")
RESCAN_BANG = p.msg(410, 480, "bang")

p.connect(LB, 0, DSP_ON, 0)
p.connect(LB, 0, GAIN, 0)
p.connect(GAIN, 0, MASTER, 1)
p.connect(LB, 0, LOAD0, 0)
p.connect(LOAD0, 0, FILE_POLY, 0)
# rescan after the fixture load has had a moment to land, so the fake
# daemon's device reply and the key-press simulation land on a patch
# that's already able to actually play something
p.connect(LB, 0, RESCAN, 0)
p.connect(RESCAN, 0, RESCAN_BANG, 0)
p.connect(RESCAN_BANG, 0, SERIALOSC, 0)

# --- capture window + write + quit ---
ARM_DELAY = p.obj(20, 520, "delay 1000")
ARM_BANG = p.msg(20, 560, "bang")
p.connect(LB, 0, ARM_DELAY, 0)
p.connect(ARM_DELAY, 0, ARM_BANG, 0)
p.connect(ARM_BANG, 0, TAPWRITE, 0)

WRITE_DELAY = p.obj(150, 520, "delay 2000")
WRITE_MSG = p.msg(150, 560, "write /tmp/mlrv_e2e_cap.wav mlrv-e2e-cap")
SF = p.obj(150, 600, "soundfiler")
p.connect(LB, 0, WRITE_DELAY, 0)
p.connect(WRITE_DELAY, 0, WRITE_MSG, 0)
p.connect(WRITE_MSG, 0, SF, 0)

QUIT_DELAY = p.obj(280, 520, "delay 2100")
QUIT_MSG = p.msg(280, 560, "\\; pd quit")
p.connect(LB, 0, QUIT_DELAY, 0)
p.connect(QUIT_DELAY, 0, QUIT_MSG, 0)

p.write("../test_mlrv.pd")
print("wrote test_mlrv.pd:", len(p.objs), "objects,", len(p.conns), "connections")
