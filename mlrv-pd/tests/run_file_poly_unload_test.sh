#!/usr/bin/env bash
# Verifies file_poly.pd sample-memory management: `unload <slot>` and `query`.
#
# Timeline exercised (all inside test_file_poly_unload.pd):
#   load 0 <ramp 4410> / load 3 <const 2205>
#   query            -> exact 8-line ascending dump of tracked occupancy
#   unload 3         -> fp: loaded 3 0; array silenced + shrunk to 64
#   probes           -> size == 64, cells 0/63 == 0
#   query            -> dump again, slot 3 now 0, rest unchanged
#   unload 9         -> out of range: no report, no error
#   playv 1 3 1 0 64 -> captured audio must be ~silence (emptied slot)
#   load 3 <const>   -> slot reusable (loaded 3 2205, size back to 2205)
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fp-unload-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/cap.wav"

N_LONG=4410
N_SHORT=2205
CONST_PEAK=12000

python3 mlrv-pd/tests/gen_test_wav.py "$OUT/fp_long.wav"  "$N_LONG"  ramp  || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/fp_short.wav" "$N_SHORT" const "$CONST_PEAK" || exit 1

# test_file_poly_unload.pd hardcodes these paths -- keep in sync.
cp "$OUT/fp_long.wav"  /tmp/mlrv_fp_long.wav
cp "$OUT/fp_short.wav" /tmp/mlrv_fp_short.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly_unload.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_fp_unload_cap.wav "$OUT/cap.wav" 2>/dev/null

PASS=()
FAIL=()

if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

# --- exact full loaded-line sequence (loads, q1 dump, unload, q2 dump, reload) ---
EXPECTED="loaded 0 4410|loaded 3 2205|loaded 0 4410|loaded 1 0|loaded 2 0|loaded 3 2205|loaded 4 0|loaded 5 0|loaded 6 0|loaded 7 0|loaded 3 0|loaded 0 4410|loaded 1 0|loaded 2 0|loaded 3 0|loaded 4 0|loaded 5 0|loaded 6 0|loaded 7 0|loaded 3 2205"
GOT="$(grep -o '^fp: loaded [0-9]* [0-9]*' "$OUT/pd.log" | sed 's/^fp: //' | tr '\n' '|' | sed 's/|$//')"
if [ "$GOT" = "$EXPECTED" ]; then
    PASS+=("exact loaded sequence (loads + q1 + unload + q2 + reload)")
else
    FAIL+=("loaded sequence mismatch: got '$GOT'")
fi

if grep -q 'loaded 9' "$OUT/pd.log"; then
    FAIL+=("unload 9 produced no report")
else
    PASS+=("unload 9 produced no report")
fi

if grep -q '^fp: loaded 0 0' "$OUT/pd.log"; then
    FAIL+=("no premature loaded 0 0")
else
    PASS+=("no premature loaded 0 0")
fi

# --- python analysis of probes + silence capture ---
PYOUT="$(python3 - "$OUT/pd.log" "$OUT/cap.wav" <<'EOF'
import re, struct, sys, wave

log, cap = sys.argv[1], sys.argv[2]
text = open(log).read()

def vals(name):
    return [float(x) for x in re.findall(rf"^{name}: (\S+)", text, re.M)]

rows = []
ok = lambda cond, msg: (f"PASS {msg}" if cond else f"FAIL {msg}", cond)

sizes = vals("size")
cells = vals("cell")
rows.append(ok(sizes == [64.0, 2205.0],
               f"slot-3 size 64 after unload, 2205 after reload (got {sizes})"))
rows.append(ok(len(cells) == 4 and all(abs(c) < 0.003 for c in cells[:2])
               and all(abs(c - 12000 / 32768.0) < 0.003 for c in cells[2:]),
               f"slot-3 cells silent after unload, const after reload (got {cells})"))

try:
    with wave.open(cap, "rb") as w:
        n = w.getnframes()
        data = struct.unpack("<" + str(n) + "h", w.readframes(n))
    peak = max(abs(x) for x in data)
    rows.append(ok(n == 4410 and peak < 50,
                   f"emptied-slot capture silent (n={n}, peak={peak})"))
except FileNotFoundError:
    rows.append((f"FAIL silence capture: wav was not written", False))

for r, _ in rows:
    print(r)
print("FAIL" if any(not ok for _, ok in rows) else "PASS")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q '^FAIL'; then FAIL+=("python analysis"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
