#!/usr/bin/env bash
# Verifies semitones_to_rate.pd against known values of the original's own
# formula (plx.maxpat: pow(2, semitones/12)) -- not just "loads clean", the
# actual arithmetic. Six values: unison, +1 octave, -1 octave, a perfect
# fifth up/down, and +2 octaves, each computed independently in Python and
# compared against Pd's own [expr] output within a tight tolerance.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-semitones-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 3 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_semitones_to_rate.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/pd.log" <<'EOF'
import sys, re

path = sys.argv[1]
with open(path) as f:
    log = f.read()

expected = {
    "r_0": 2 ** (0 / 12),
    "r_12": 2 ** (12 / 12),
    "r_neg12": 2 ** (-12 / 12),
    "r_7": 2 ** (7 / 12),
    "r_neg7": 2 ** (-7 / 12),
    "r_24": 2 ** (24 / 12),
}

ok = True
for name, want in expected.items():
    m = re.search(rf"^{re.escape(name)}: (-?[\d.]+)$", log, re.MULTILINE)
    if not m:
        print(f"FAIL {name}: not found in pd log")
        ok = False
        continue
    got = float(m.group(1))
    if abs(got - want) < 1e-3:
        print(f"PASS {name} = {got:.5f} (expected {want:.5f})")
    else:
        print(f"FAIL {name} = {got:.5f}, expected {want:.5f}")
        ok = False

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("semitones_to_rate arithmetic check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
