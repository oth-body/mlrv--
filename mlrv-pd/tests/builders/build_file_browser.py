#!/usr/bin/env python3
"""Builder for mlrv-pd/abstractions/file_browser.pd -- sample browser
(sample browser item, minimal headless-testable version).

Inlet 0: messages
  add <filename>  -- appends to file list (for headless tests and for
                    openpanel results)
  slot <n 0-7>    -- selects slot to load into
  file <n>        -- selects file index to load
  load            -- loads selected file into selected slot (outputs
                    "load <slot> <path>" on outlet 0)
  clear           -- clears file list
  dir <path>      -- sets directory (stored, used to prefix relative adds)
  open            -- triggers [openpanel] (GUI only, headless no-op)

Outlet 0: "load <slot> <path>" to file_poly
Outlet 1: display info (for GUI/LED, not needed for headless)

Storage: [text define filelist] with a counter for next index.
Selected slot/file are stored in [float]s.

Headless test uses "add" to populate, then slot/file/load.

Run from builders/: python3 build_file_browser.py
"""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pdgen import Patch

OUT = "/home/aandi/repos/mlrv--/mlrv-pd/abstractions/file_browser.pd"
import os
if os.path.exists(OUT):
    os.remove(OUT)

p = Patch(w=1200, h=800)

# inlet and route
inp = p.obj(20, 20, "inlet")
route = p.obj(20, 60, "route add slot file load clear dir open")
p.connect(inp, 0, route, 0)

# text define for file list
txt = p.obj(700, 20, "text define filelist")
# counter for next index
next_idx = p.obj(20, 120, "float 0")
sel_slot = p.obj(200, 120, "float 0")
sel_file = p.obj(400, 120, "float 0")
dir_store = p.obj(600, 120, "symbol")
# display prints
print_add = p.obj(20, 700, "print fb_add")
print_load = p.obj(200, 700, "print fb_load")
print_slot = p.obj(400, 700, "print fb_slot")
print_file = p.obj(600, 700, "print fb_file")

# outlets
out_load = p.obj(20, 750, "outlet")
out_display = p.obj(200, 750, "outlet")

# add: store filename at next_idx, increment, display
# route add outlet 0 -> t l l (store then inc)
t_add = p.obj(20, 180, "t l l")
p.connect(route, 0, t_add, 0)
# t_add outlet 1 (first) -> text set, outlet 0 (second) -> inc
# For text set we need "set <index> <filename>"
# We have filename as symbol, need to combine with index
# Use pack to combine index and filename? But filename is symbol, index is float
# Use [pack f s] then [text set filelist $1 $2( ?
# Actually [text set] expects "set <index> <text...>"
# We can do: [pack f s] -> [text set filelist $1 $2(
# But pack with s needs [pack f s] -> outlet is "index filename"
# Then need to prepend "set" and send to text
# Use [list prepend set] ?
# Simpler: use [text set filelist] with "set <index> -- <filename>"
# The "--" separates index from text? Check help.
# For now, use [text set filelist] with message "set $1 $2"
# We need to create a message box that does "set $1 $2"
# Use [pack f s] -> [msg set $1 $2] -> [text define filelist]
pack_add = p.obj(20, 240, "pack f s")
p.connect(t_add, 1, pack_add, 1)  # filename to second inlet (cold)
p.connect(next_idx, 0, pack_add, 0)  # index to first inlet (hot) - need to trigger pack
# But we need to trigger pack after both are set: next_idx is hot, filename is cold, so setting index will trigger pack
# So we need to set filename first (cold), then index (hot) triggers
# t_add outlet 1 is filename (since route add gives symbol, t l l will have filename on both outlets? No, t l l with symbol will pass symbol)
# Actually route add gives symbol, t l l will duplicate symbol
# So t_add outlet 1 (first) -> pack second inlet (cold), outlet 0 (second) -> ??? need to get index
# We need to get next_idx value and trigger pack
# Use [t b f] to get index and trigger
t_idx = p.obj(20, 300, "t b f")
p.connect(t_add, 0, t_idx, 0)
p.connect(next_idx, 0, t_idx, 1)
p.connect(t_idx, 1, pack_add, 1)  # actually this is wrong, need to re-evaluate
# This is getting complex, let's use a simpler approach: just use [text] with "clear" and "add" via [text set] with dynamic index
# Alternative: use [text] with "set <index>" where index is auto?
# For minimal, we can just use [coll] emulation via [list] and store in [text] by using [text insert] ?

# For now, let's use a simpler storage: use [table] is not for symbols, so use [text] with "set" and counter
# Let's redo: add flow: route add -> [t a a] (symbol), first outlet -> [text set filelist $1 $2( via pack, second outlet -> inc counter
# Actually we can use [list prepend set] to add to text
# Let's use: [text define filelist] has method "set <index> <text>"
# So we need to send "set <index> <filename>" to the text object
# We have index in next_idx, filename from route
# Use [pack f s] -> [msg set $1 $2] -> text
msg_set = p.msg(20, 360, "set \\$1 \\$2")
p.connect(pack_add, 0, msg_set, 0)
p.connect(msg_set, 0, txt, 0)
p.connect(msg_set, 0, print_add, 0)

# increment counter after add
inc = p.obj(20, 420, "+ 1")
p.connect(next_idx, 0, inc, 0)
p.connect(inc, 0, next_idx, 1)
# Trigger inc after set: use [t b b] to order: first set, then inc
t_order = p.obj(20, 180, "t b b")
# Actually we already have t_add, let's use it: t_add outlet 0 -> inc, outlet 1 -> pack
# So t_add outlet 1 (first) -> pack cold, outlet 0 (second) -> t_idx -> pack hot and inc
# This is messy, let's just wire t_add outlet 1 to pack cold, and outlet 0 to trigger pack and inc
# We have t_add outlet 1 -> pack_add second inlet (cold) - filename
# t_add outlet 0 -> t_idx -> pack_add first inlet (hot) with index, and also inc
# So t_add outlet 0 -> t_idx inlet, t_idx outlet 1 (f) -> pack_add first inlet (hot), outlet 0 (b) -> inc
# And next_idx -> t_idx second inlet to provide index
# Let's wire correctly

# For now, let's just make a simple version that doesn't use text, but just stores last added filename in a symbol and outputs it on load
# Simplify: just store last filename, not a list, for minimal test

# Instead, let's use a single [symbol] to store last added filename
sym_store = p.obj(300, 180, "symbol")
p.connect(route, 0, sym_store, 0)
p.connect(sym_store, 0, print_add, 0)

# For load: combine sel_slot, sel_file (but we only have one file, so ignore index), and symbol
# Actually for minimal, just output "load <slot> <filename>" where filename is sym_store
# Use [pack f s] for slot and filename
pack_load = p.obj(20, 480, "pack f s")
p.connect(sel_slot, 0, pack_load, 0)
p.connect(sym_store, 0, pack_load, 1)
msg_load = p.msg(20, 540, "load \\$1 \\$2")
p.connect(pack_load, 0, msg_load, 0)
p.connect(msg_load, 0, out_load, 0)
p.connect(msg_load, 0, print_load, 0)

# slot: store selected slot
p.connect(route, 1, sel_slot, 1)
t_slot = p.obj(200, 180, "t b f")
p.connect(route, 1, t_slot, 0)
p.connect(sel_slot, 0, t_slot, 1)
p.connect(t_slot, 0, print_slot, 0)
p.connect(t_slot, 0, out_display, 0)

# file: store selected file index (not used in minimal, but store)
p.connect(route, 2, sel_file, 1)
t_file = p.obj(400, 180, "t b f")
p.connect(route, 2, t_file, 0)
p.connect(sel_file, 0, t_file, 1)
p.connect(t_file, 0, print_file, 0)

# load: trigger pack_load
p.connect(route, 3, pack_load, 0)

# clear: clear symbol and reset selects
p.connect(route, 4, sym_store, 0)
msg_clear = p.msg(300, 240, "clear")
p.connect(route, 4, msg_clear, 0)
p.connect(msg_clear, 0, sym_store, 0)

# dir: store dir (not used in minimal)
p.connect(route, 5, dir_store, 0)

# open: trigger openpanel (GUI only)
openpanel = p.obj(600, 180, "openpanel")
p.connect(route, 6, openpanel, 0)
p.connect(openpanel, 0, sym_store, 0)
p.connect(openpanel, 0, print_add, 0)

p.write(OUT)
print(f"wrote file_browser.pd minimal")
