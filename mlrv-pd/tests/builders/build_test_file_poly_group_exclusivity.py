#!/usr/bin/env python3
"""Builder for mlrv-pd/tests/test_file_poly_group_exclusivity.pd.

Verifies real mute-group behavior against real audio, not just "loads
clean": same-group cancellation, different-group non-interference,
ungrouped (group 0) non-interference, and groupstop. Four const
fixtures at distinct, summable peaks (16000/8000/4000/2000) let a
single summed capture unambiguously reveal which voices are actually
still sounding at each stage.

Timeline (slot0/1 -> group1, slot2 -> group2, slot3 stays group0/ungrouped):
  playv 1 slot0 (group1)                         -> capture_a: ~16000 (voice1 alone)
  playv 2 slot1 (group1, SAME -> cancels voice1)  -> capture_b: ~8000  (voice1 gone)
  playv 3 slot2 (group2, DIFFERENT -> no cancel)  -> capture_c: ~12000 (voice2+3)
  playv 4 slot3 (group0/ungrouped -> no cancel)   -> capture_d: ~14000 (voice2+3+4)
  groupstop 1 (stops whatever's in group1 = voice2) -> capture_e: ~6000 (voice3+4 only)

Run from builders/: python3 build_test_file_poly_group_exclusivity.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

N = 2205
p = Patch(w=1400, h=900)

lb = p.obj(20, 20, "loadbang")
dsp = p.msg(200, 20, "\\; pd dsp 1")
p.connect(lb, 0, dsp, 0)

fp = p.obj(20, 80, "file_poly")
pr = p.obj(20, 130, "print fp")
p.connect(fp, 1, pr, 0)

loads = [
    p.msg(100, 200 + 30 * i, f"load {i} /tmp/mlrv_fpge_s{i}.wav")
    for i in range(4)
]
m_group0 = p.msg(300, 200, "group 0 1")
m_group1 = p.msg(300, 230, "group 1 1")
m_group2 = p.msg(300, 260, "group 2 2")
# slot 3 stays default (group 0 = ungrouped)

playv = [
    p.msg(500, 200, f"playv 1 0 1 0 {N}"),
    p.msg(500, 230, f"playv 2 1 1 0 {N}"),
    p.msg(500, 260, f"playv 3 2 1 0 {N}"),
    p.msg(500, 290, f"playv 4 3 1 0 {N}"),
]
m_groupstop1 = p.msg(500, 330, "groupstop 1")

for m in loads + [m_group0, m_group1, m_group2] + playv + [m_groupstop1]:
    p.connect(m, 0, fp, 0)

caps = ["capture_a", "capture_b", "capture_c", "capture_d", "capture_e"]
tws = [p.obj(700, 200 + 40 * i, f"tabwrite~ {c}") for i, c in enumerate(caps)]
for tw in tws:
    p.connect(fp, 0, tw, 0)

arms = [p.obj(650, 400 + 30 * i, "t b b") for i in range(5)]
for i, arm in enumerate(arms):
    p.connect(arm, 0, tws[i], 0)

# arm[0..3] also fire their playv; arm[4] fires groupstop
for i in range(4):
    p.connect(arms[i], 1, playv[i], 0)
p.connect(arms[4], 1, m_groupstop1, 0)

for i, c in enumerate(caps):
    p.obj(900, 200 + 30 * i, f"table {c} {N}")

writes = []
for c in caps:
    wmsg = p.msg(1100, 200 + 40 * len(writes), f"write /tmp/mlrv_fpge_{c}.wav {c}")
    wr = p.obj(1250, 200 + 40 * len(writes), "soundfiler")
    p.connect(wmsg, 0, wr, 0)
    writes.append(wmsg)

p.timeline(20, 600, [
    (50, None, loads[0], 0),
    (60, None, loads[1], 0),
    (70, None, loads[2], 0),
    (80, None, loads[3], 0),
    (200, None, m_group0, 0),
    (210, None, m_group1, 0),
    (220, None, m_group2, 0),
    (350, None, arms[0], 0),
    (500, None, arms[1], 0),
    (650, None, arms[2], 0),
    (800, None, arms[3], 0),
    (950, None, arms[4], 0),
    (1100, None, writes[0], 0),
    (1110, None, writes[1], 0),
    (1120, None, writes[2], 0),
    (1130, None, writes[3], 0),
    (1140, None, writes[4], 0),
])

p.write("/home/aandi/repos/mlrv--/mlrv-pd/tests/test_file_poly_group_exclusivity.pd")
print("wrote test_file_poly_group_exclusivity.pd")
