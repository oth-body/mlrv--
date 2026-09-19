#!/usr/bin/env bash
# Verifies file_poly.pd's automatic mute-group exclusivity and groupstop
# against real captured audio -- not just "loads clean". Four const
# fixtures at distinct, summable peaks let one summed capture per stage
# unambiguously reveal which voices are still sounding. See
# tests/builders/build_test_file_poly_group_exclusivity.py for the full
# scenario (same-group cancellation, different-group non-interference,
# ungrouped non-interference, groupstop).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fpge-test"
mkdir -p "$OUT"
rm -f "$OUT"/*.wav "$OUT/pd.log"

PEAKS=(16000 8000 4000 2000)
for i in 0 1 2 3; do
    python3 mlrv-pd/tests/gen_test_wav.py "$OUT/s$i.wav" 2205 const "${PEAKS[$i]}" || exit 1
    cp "$OUT/s$i.wav" "/tmp/mlrv_fpge_s$i.wav"
done

timeout 6 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly_group_exclusivity.pd > "$OUT/pd.log" 2>&1

for c in capture_a capture_b capture_c capture_d capture_e; do
    cp "/tmp/mlrv_fpge_${c}.wav" "$OUT/${c}.wav" 2>/dev/null
done

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT" <<'EOF'
import sys, wave, struct

out = sys.argv[1]
SKIP = 400  # 5ms cold-start fade margin

def plateau(name):
    path = f"{out}/{name}.wav"
    try:
        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        print(f"FAIL {path} was not written")
        sys.exit(1)
    n = len(vals)
    return sum(vals[SKIP:]) / (n - SKIP)

def check(label, got, want, tol=600):
    ok = abs(got - want) < tol
    print(f"{'PASS' if ok else 'FAIL'} {label}: {got:.0f} (expected ~{want}, tol {tol})")
    return ok

ok = True
ok &= check("stage A: voice1 alone (slot0, group1)", plateau("capture_a"), 16000)
ok &= check("stage B: voice2 triggers, SAME group1 -> voice1 cancelled", plateau("capture_b"), 8000)
ok &= check("stage C: voice3 triggers, group2 (different) -> voice2 survives", plateau("capture_c"), 8000 + 4000)
ok &= check("stage D: voice4 triggers, group0 (ungrouped) -> nothing cancelled", plateau("capture_d"), 8000 + 4000 + 2000)
ok &= check("stage E: groupstop 1 -> voice2 (group1) stopped, voice3+4 remain", plateau("capture_e"), 4000 + 2000)

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("group exclusivity content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
