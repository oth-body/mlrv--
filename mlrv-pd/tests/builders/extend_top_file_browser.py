#!/usr/bin/env python3
"""Extend mlrv.pd and mlrv-gui.pd to wire file_browser (sample browser item).

- Adds file_browser abstraction (inlet file_browser, outlet to file_poly)
- Wires mapping outlet 5 -> file_browser -> file_poly
- For mlrv-gui, also adds openpanel GUI

Refuses to run twice per file.
"""
import sys
for path, is_gui in [("/home/aandi/repos/mlrv--/mlrv-pd/mlrv.pd", False),
                     ("/home/aandi/repos/mlrv--/mlrv-pd/mlrv-gui.pd", True)]:
    with open(path) as f:
        lines = f.read().splitlines()
    if any("file_browser" in l for l in lines):
        print(f"skip {path} already wired")
        continue
    body = [l for l in lines[1:] if l.startswith("#X ") and not l.startswith("#X connect")]
    conns = [l for l in lines[1:] if l.startswith("#X connect")]
    # Find file_poly and mapping indices via obj search
    fpoly_idx = next(i for i,l in enumerate(body) if l.startswith("#X obj") and "file_poly" in l and "file_browser" not in l)
    mapping_idx = next(i for i,l in enumerate(body) if l.startswith("#X obj") and l.strip().endswith("mapping;"))
    # Find mixer and master for context, but not needed
    # Add file_browser object
    # Position: near file_poly, y=340
    fb_idx = len(body)
    body.append(f"#X obj 300 340 file_browser;")
    # Connect mapping outlet 5 -> file_browser
    # mapping outlet 5 is file_browser (new), need to find mapping's outlet count
    # mapping has 6 outlets now (0 file_poly,1 grid,2 beat,3 pattern,4 record,5 file_browser)
    # In mlrv.pd, mapping is at 300 320, file_browser at 300 340, file_poly at 300 200
    # Connect mapping 5 -> file_browser 0
    conns.append(f"#X connect {mapping_idx} 5 {fb_idx} 0;")
    # Connect file_browser 0 -> file_poly 0
    conns.append(f"#X connect {fb_idx} 0 {fpoly_idx} 0;")
    # For GUI, also add a simple openpanel button (already inside file_browser, but we can add a GUI button that sends "open" to file_browser)
    if is_gui:
        # Add a bang that sends "open" to file_browser
        btn_idx = len(body)
        body.append(f"#X obj 800 340 bng 20 250 50 0 empty empty open 0 -8 0 10 #dfdfdf #000000 #000000;")
        msg_idx = len(body)
        body.append(f"#X msg 800 380 open;")
        conns.append(f"#X connect {btn_idx} 0 {msg_idx} 0;")
        conns.append(f"#X connect {msg_idx} 0 {fb_idx} 0;")
        body.append(f"#X text 800 400 file browser open (GUI) -- 2026-09-18 sample browser;")
    else:
        body.append(f"#X text 300 380 file_browser wiring -- 2026-09-18 sample browser;")

    with open(path, "w") as f:
        f.write("\n".join([lines[0]] + body + conns) + "\n")
    print(f"wired file_browser in {path}")
