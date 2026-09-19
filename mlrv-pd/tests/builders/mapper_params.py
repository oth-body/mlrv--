#!/usr/bin/env python3
"""Shared mapper PARAMS table (1:1 mlrv recreation, item 5 mapping GUI).

Single source of truth for mappable endpoints, imported by
build_mapper.py (the binding engine) and build_mlrv_gui.py (the widget
surface) so widget->engine messages and mapper dispatch formats can never
drift apart. First 7 entries are frozen (run_mapper_test asserts indices).

kinds: cont (scaled float), dint (scaled+rounded int), dsym (int 0/1 picks
two symbol messages), trig (fixed message on any ctl).
"""

PARAMS = [
    {"sym": "tempo",      "kind": "cont", "min": 60, "max": 180, "fmt": "tempo \\$1", "gui": "hsl", "dst": "mapping"},
    {"sym": "master",     "kind": "cont", "min": 0,  "max": 1.5, "fmt": "\\$1", "gui": "hsl", "dst": "master"},
    {"sym": "vol0",       "kind": "cont", "min": 0,  "max": 1,   "fmt": "vol 0 \\$1", "gui": None, "dst": None},
    {"sym": "vgain1",     "kind": "cont", "min": 0,  "max": 2,   "fmt": "gain 1 \\$1", "gui": "hsl", "dst": "file_poly"},
    {"sym": "vmode1",     "kind": "dsym", "min": 0,  "max": 1,   "m0": "mode 1 loop", "m1": "mode 1 shot", "gui": "2bang", "dst": "file_poly"},
    {"sym": "sgroup0",    "kind": "dint", "min": 0,  "max": 4,   "fmt": "group 0 \\$1", "gui": "num", "dst": "file_poly"},
    {"sym": "groupstop1", "kind": "trig", "min": 0,  "max": 1,   "fmt": "groupstop 1", "gui": "bang", "dst": "file_poly"},
    {"sym": "quantize",   "kind": "cont", "min": 0.25, "max": 4, "fmt": "quantize \\$1", "gui": "hsl", "dst": "mapping"},
]
for i in (1, 2, 3):
    PARAMS.append({"sym": f"vol{i}", "kind": "cont", "min": 0, "max": 1, "fmt": f"vol {i} \\$1", "gui": None, "dst": None})
for i in range(4):
    PARAMS.append({"sym": f"send{i}", "kind": "cont", "min": 0, "max": 1, "fmt": f"send {i} \\$1", "gui": None, "dst": None})
for v in (2, 3, 4):
    PARAMS.append({"sym": f"vgain{v}", "kind": "cont", "min": 0, "max": 2, "fmt": f"gain {v} \\$1", "gui": "hsl", "dst": "file_poly"})
for v in (1, 2, 3, 4):
    PARAMS.append({"sym": f"vpitch{v}", "kind": "cont", "min": -12, "max": 12, "fmt": f"pitch {v} \\$1", "gui": "hsl", "dst": "file_poly"})
for v in (2, 3, 4):
    PARAMS.append({"sym": f"vmode{v}", "kind": "dsym", "min": 0, "max": 1,
                   "m0": f"mode {v} loop", "m1": f"mode {v} shot", "gui": "2bang", "dst": "file_poly"})
for s in range(1, 8):
    PARAMS.append({"sym": f"sgroup{s}", "kind": "dint", "min": 0, "max": 4, "fmt": f"group {s} \\$1", "gui": "num", "dst": "file_poly"})
for s in range(8):
    PARAMS.append({"sym": f"sslave{s}", "kind": "dint", "min": 0, "max": 1, "fmt": f"slave {s} \\$1", "gui": "tgl", "dst": "mapping"})
for g in (2, 3, 4):
    PARAMS.append({"sym": f"groupstop{g}", "kind": "trig", "min": 0, "max": 1, "fmt": f"groupstop {g}", "gui": "bang", "dst": "file_poly"})
PARAMS += [
    {"sym": "pat_arm",    "kind": "trig", "min": 0, "max": 1, "fmt": "arm", "gui": "bang", "dst": "pattern"},
    {"sym": "pat_play",   "kind": "trig", "min": 0, "max": 1, "fmt": "play", "gui": "bang", "dst": "pattern"},
    {"sym": "pat_stop",   "kind": "trig", "min": 0, "max": 1, "fmt": "stop", "gui": "bang", "dst": "pattern"},
    {"sym": "pat_clear",  "kind": "trig", "min": 0, "max": 1, "fmt": "clear", "gui": "bang", "dst": "pattern"},
    {"sym": "pat_length", "kind": "cont", "min": 250, "max": 8000, "fmt": "length \\$1", "gui": "hsl", "dst": "pattern"},
    {"sym": "rec_record", "kind": "trig", "min": 0, "max": 1, "fmt": "record", "gui": "bang", "dst": "record"},
    {"sym": "rec_loop",   "kind": "dint", "min": 0, "max": 1, "fmt": "loop \\$1", "gui": "tgl", "dst": "record"},
]
assert [p["sym"] for p in PARAMS[:7]] == ["tempo", "master", "vol0", "vgain1", "vmode1", "sgroup0", "groupstop1"], \
    "first 7 params must stay fixed (run_mapper_test asserts their indices)"
