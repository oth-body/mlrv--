#!/usr/bin/env python3
"""Builder for mlrv-pd/mlrv-gui.pd -- the literal mapping GUI (1:1 mlrv
recreation, item 5 mapping GUI, increment 2): a Pd-native widget surface
plus the full engine, runnable with a real GUI (`run_mlrv_gui.sh`) and
headless-verifiable (`run_mlrv_gui_test.sh` sends the identical bytes the
widgets emit -- widgets themselves can't move without a display).

Contents:
- ENGINE (mirrors mlrv.pd exactly): serialosc/grid/file_poly/mapping/
  mixer/master/dac~, `delay_fx~` + `reverb_fx~` (the real effects between
  mixer's fxout and master's fxin, summed via a plain [+~] into the one
  real send~ fxin -- see build_delay_fx.py's docstring for why each
  effect gets a real outlet~ rather than its own bus-based send~ fxin;
  replaces the old sig~0/send~fxin silencer stub), demo sample loads, DSP
  on, master 0.8. vol/send params stay message-only past the mixer, their
  dispatch outlets deliberately unconnected (see demux below), never
  misrouted.
- pattern_recorder (outlet0 plays back into mapping.pd's grid dispatch,
  exactly as designed) + record_buffer~ mlrv-rec on adc~ 1 (live input;
  silent headless -- the test asserts done-bang + path, not content).
- mapper + osc/midi/key adapters feeding its inlet; dispatch demux:
  rC1 (arm/play/stop/clear/length -> pattern; FIRST so bare play/stop can
  never reach file_poly's arg-carrying play/stop), rC2 (record/loop ->
  record), rA (tempo/quantize/slave -> mapping), rB (gain/pitch/mode/group/
  groupstop -> file_poly; vol/send matched and DROPPED), reject (bare
  floats only -- master gain) -> master.
- WIDGETS: one row per GUI param from mapper_params.PARAMS (widget emits
  the identical fmt bytes as mapper dispatch -- same table, no drift):
  hsl (cont, direct ranges incl. negatives/fractions -- probe-verified),
  floatatom (dint), tgl (0/1 dints), msg-buttons (dsym pairs, trigs incl.
  pattern/record transports, which are DIRECT widget->engine, not mapper).
  Every mapped widget gets a `learn <sym>` msg-button (click = arm).
- Shared min/max editor row (idx/min/max atoms + apply -> `mini/maxi`),
  mapping-status line (mapper outlet1 -> `set ...` into a visible msg).

Widget syntax (hsl/bng/tgl/floatatom creation lines) copied from Pd's own
bundled help patches, load-verified in /tmp/widget_probe.pd before
generating ~150 of them.

Run from builders/: python3 build_mlrv_gui.py
"""
import os
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch
from mapper_params import PARAMS

OUT = "/home/aandi/repos/mlrv--/mlrv-pd/mlrv-gui.pd"
assert not os.path.exists(OUT), "mlrv-gui.pd exists -- refusing to double-build"

GUI = [p for p in PARAMS if p["gui"] is not None]

p = Patch(w=1700, h=2700)
p.text(20, 20, "mlrv-gui.pd -- literal mapping GUI + full instrument (1:1 mlrv recreation item 5 \\, increment 2). widgets send engine messages directly (always live) \\; MIDI/OSC/key go through mapper.pd (learn buttons arm params). run WITH a display: mlrv-pd/run_mlrv_gui.sh. headless: run_mlrv_gui_test.sh.")

# ---------------- engine (mirrors mlrv.pd) ----------------
sosc = p.obj(20, 80, "serialosc 8000 /monome")
grid = p.obj(20, 140, "grid")
fpoly = p.obj(300, 80, "file_poly")
mapping = p.obj(300, 200, "mapping")
mixer = p.obj(460, 80, "mixer")
master = p.obj(600, 80, "master")
delay = p.obj(600, 200, "delay_fx~")
reverb = p.obj(720, 200, "reverb_fx~")
fx_sum = p.obj(600, 230, "+~")
fx_send = p.obj(600, 260, "send~ fxin")
dac = p.obj(600, 280, "dac~ 1 2")
prec = p.obj(900, 80, "pattern_recorder")
rbuf = p.obj(900, 200, "record_buffer~ mlrv-rec")
rectab = p.obj(900, 260, "table mlrv-rec 220500")
adc = p.obj(900, 140, "adc~ 1")
patlive = p.obj(1150, 80, "print pat-live")
recdone = p.obj(1150, 200, "print rec-done")
p.connect(sosc, 1, mapping, 0)
p.connect(fpoly, 1, mapping, 1)
p.connect(mapping, 0, fpoly, 0)
p.connect(mapping, 1, grid, 0)
p.connect(grid, 0, sosc, 1)
p.connect(fpoly, 2, mixer, 0)
p.connect(fpoly, 3, mixer, 1)
p.connect(fpoly, 4, mixer, 2)
p.connect(fpoly, 5, mixer, 3)
p.connect(mixer, 0, master, 0)
p.connect(delay, 0, fx_sum, 0)
p.connect(reverb, 0, fx_sum, 1)
p.connect(fx_sum, 0, fx_send, 0)
p.connect(master, 0, dac, 0)
p.connect(master, 0, dac, 1)
p.connect(prec, 0, mapping, 0)
p.connect(prec, 1, patlive, 0)
p.connect(adc, 0, rbuf, 0)
p.connect(rbuf, 1, recdone, 0)

lb = p.obj(20, 340, "loadbang")
m_dsp = p.msg(20, 380, "\\; pd dsp 1")
m_gain = p.msg(150, 380, "0.8")
m_scan = p.msg(280, 380, "bang")
m_l0 = p.msg(410, 380, "load 0 demo-tone-0.wav")
m_l1 = p.msg(410, 420, "load 1 demo-tone-1.wav")
t5 = p.obj(20, 340 - 40, "t b b b b b")
p.connect(lb, 0, t5, 0)
p.connect(t5, 4, m_dsp, 0)
p.connect(t5, 3, m_gain, 0)
p.connect(m_gain, 0, master, 1)
p.connect(t5, 2, m_scan, 0)
p.connect(m_scan, 0, sosc, 0)
p.connect(t5, 1, m_l0, 0)
p.connect(m_l0, 0, fpoly, 0)
p.connect(t5, 0, m_l1, 0)
p.connect(m_l1, 0, fpoly, 0)

# ---------------- mapper + adapters + demux + status ----------------
mapper = p.obj(20, 480, "mapper")
oscc = p.obj(300, 480, "osc_ctl 9000")
midic = p.obj(470, 480, "midi_ctl")
keyc = p.obj(640, 480, "key_ctl")
p.connect(oscc, 0, mapper, 0)
p.connect(midic, 0, mapper, 0)
p.connect(keyc, 0, mapper, 0)

rC1 = p.obj(20, 560, "route arm play stop clear length")
rC2 = p.obj(20, 610, "route record loop")
rA = p.obj(20, 660, "route tempo quantize slave")
rB = p.obj(20, 710, "route gain pitch mode group groupstop vol send")
p.connect(mapper, 0, rC1, 0)
p.connect(rC1, 5, rC2, 0)
for i in range(5):
    p.connect(rC1, i, prec, 0)
p.connect(rC2, 2, rA, 0)
p.connect(rC2, 0, rbuf, 1)
p.connect(rC2, 1, rbuf, 1)
p.connect(rA, 3, rB, 0)
for i in range(3):
    p.connect(rA, i, mapping, 0)
for i in range(5):
    p.connect(rB, i, fpoly, 0)
p.connect(rB, 5, mixer, 4)
p.connect(rB, 6, mixer, 4)
p.connect(rB, 7, master, 1)

rstat = p.obj(900, 480, "route learning bound")
setL = p.msg(900, 530, "set learning \\$1")
setB = p.msg(1050, 530, "set bound \\$1 \\$2")
statmsg = p.msg(900, 580, "mapping idle")
statprint = p.obj(1150, 530, "print map-status")
p.connect(mapper, 1, rstat, 0)
p.connect(rstat, 0, setL, 0)
p.connect(setL, 0, statmsg, 0)
p.connect(rstat, 1, setB, 0)
p.connect(setB, 0, statmsg, 0)
p.connect(setL, 0, statprint, 0)
p.connect(setB, 0, statprint, 0)

# shared min/max editor row. atoms write SILENT stores (right inlets), so
# editing idx/min/max directly never fires anything; apply re-emits in
# cold-first order (min, max, then idx hot into both packs).
p.text(20, 770, "min/max editor: set idx + ranges \\, click apply (sends mini/maxi). idx: tempo 0 master 1 vol0 2 vgain1 3 vmode1 4 sgroup0 5 groupstop1 6 quantize 7 vol1-3 8-10 send0-3 11-14 vgain2-4 15-17 vpitch1-4 18-21 vmode2-4 22-24 sgroup1-7 25-31 sslave0-7 32-39 groupstop2-4 40-42 pat_arm 43 pat_play 44 pat_stop 45 pat_clear 46 pat_length 47 rec_record 48 rec_loop 49.")
a_idx = p.floatatom(20, 800, 5)
a_min = p.floatatom(150, 800, 5)
a_max = p.floatatom(280, 800, 5)
fi = p.obj(20, 840, "float 0")
fmin = p.obj(150, 840, "float 0")
fmax = p.obj(280, 840, "float 0")
p.connect(a_idx, 0, fi, 1)
p.connect(a_min, 0, fmin, 1)
p.connect(a_max, 0, fmax, 1)
a_go = p.obj(410, 800, "bng 20 250 50 0 empty empty apply 0 -8 0 10 #dfdfdf #000000 #000000")
at1 = p.obj(470, 800, "t b b b")
pk1 = p.obj(530, 800, "pack f f")
mm1 = p.msg(530, 850, "mini \\$1 \\$2")
pk2 = p.obj(700, 800, "pack f f")
mm2 = p.msg(700, 850, "maxi \\$1 \\$2")
p.connect(a_go, 0, at1, 0)
p.connect(at1, 2, fmin, 0)
p.connect(fmin, 0, pk1, 1)
p.connect(at1, 1, fmax, 0)
p.connect(fmax, 0, pk2, 1)
p.connect(at1, 0, fi, 0)
p.connect(fi, 0, pk1, 0)
p.connect(fi, 0, pk2, 0)
p.connect(pk1, 0, mm1, 0)
p.connect(mm1, 0, mapper, 0)
p.connect(pk2, 0, mm2, 0)
p.connect(mm2, 0, mapper, 0)

# ---------------- widgets (two columns) ----------------
DST = {"mapping": mapping, "file_poly": fpoly, "master": master,
       "pattern": prec, "record": rbuf}
MINLET = {"mapping": 0, "file_poly": 0, "master": 1, "pattern": 0, "record": 1}
HSL = "hsl 140 15 %s %s 0 0 empty empty %s 0 -9 0 10 #dfdfdf #000000 #000000 0 1"

def learnbtn(bx, y, sym):
    m = p.msg(bx, y, f"learn {sym}")
    p.connect(m, 0, mapper, 0)
    return m

half = (len(GUI) + 1) // 2
for n, pr in enumerate(GUI):
    col = n // half
    row = n % half
    bx = 20 + 830 * col
    y = 880 + 46 * row
    p.text(bx, y, pr["sym"])
    dst, inl = DST[pr["dst"]], MINLET[pr["dst"]]
    g = pr["gui"]
    if g == "hsl":
        w = p.obj(bx + 150, y, HSL % (pr["min"], pr["max"], pr["sym"]))
        fm = p.msg(bx + 320, y, pr["fmt"])
        p.connect(w, 0, fm, 0)
        p.connect(fm, 0, dst, inl)
        learnbtn(bx + 480, y, pr["sym"])
    elif g == "num":
        fa = p.floatatom(bx + 150, y, 5)
        fm = p.msg(bx + 320, y, pr["fmt"])
        p.connect(fa, 0, fm, 0)
        p.connect(fm, 0, dst, inl)
        learnbtn(bx + 480, y, pr["sym"])
    elif g == "tgl":
        tg = p.obj(bx + 150, y, f"tgl 20 0 empty empty {pr['sym']} 0 -8 0 10 #dfdfdf #000000 #000000 0 1")
        fm = p.msg(bx + 320, y, pr["fmt"])
        p.connect(tg, 0, fm, 0)
        p.connect(fm, 0, dst, inl)
        learnbtn(bx + 480, y, pr["sym"])
    elif g == "2bang":
        b0 = p.msg(bx + 150, y, pr["m0"])
        b1 = p.msg(bx + 300, y, pr["m1"])
        p.connect(b0, 0, dst, inl)
        p.connect(b1, 0, dst, inl)
        learnbtn(bx + 480, y, pr["sym"])
    elif g == "bang":
        b = p.msg(bx + 150, y, pr["fmt"])
        p.connect(b, 0, dst, inl)
        learnbtn(bx + 480, y, pr["sym"])

p.write(OUT)
print(f"wrote mlrv-gui.pd: {len(GUI)} widget rows")
