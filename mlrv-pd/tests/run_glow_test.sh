#!/usr/bin/env bash
# Deterministic test for mlrv-pd/patchers/glow.pd (no hardware).
# Timeline in tests/builders/build_test_glow.py.
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-glow-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 6 pd -nogui -stderr -path mlrv-pd/patchers \
    mlrv-pd/tests/test_glow.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check() {
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}

if grep -qiE "error:|connection failed|no such object" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

# paint is instant full-bright, then phosphor decay takes over
check "$OUT/pd.log" "^gled: 2 3 15\$" "paint dot instant 2 3 15"
check "$OUT/pd.log" "^gled: 2 3 13\$" "decay step 2 3 13"
check "$OUT/pd.log" "^gled: 2 3 10\$" "decay step 2 3 10"
# spawn ball shows once decayed
check "$OUT/pd.log" "^gled: 3 3 13\$" "spawn ball visible 3 3 13"
# tilt steered the comet +x
check "$OUT/pd.log" "^gled: 4 3 13\$" "comet travelled to 4 3"
# shake cleared the frame
check "$OUT/pd.log" "^gled: 2 3 0\$" "shake clears cell 2 3"

echo "---- results"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
