#!/usr/bin/env bash
# Deterministic test for mlrv-pd/patchers/tiltvis.pd (no hardware).
# Timeline in tests/builders/build_test_tiltvis.py.
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-tiltvis-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 5 pd -nogui -stderr -path mlrv-pd/patchers \
    mlrv-pd/tests/test_tiltvis.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check() {
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}

if grep -qiE "error:|connection failed|no such object" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

# info sequence exactly: tilt report (energy 125), recenter (+energy-zero
# sync triple), tilt report
INFO="$(grep -o '^tinfo: .*' "$OUT/pd.log" | sed 's/^tinfo: //' | tr '\n' '|')"
EXPECT_INFO="tilt 177 127 125|center 177 127 127|tilt 177 127 0|tilt 127 127 125|"
if [ "$INFO" = "$EXPECT_INFO" ]; then
    PASS+=("info sequence exactly: tilt,center,sync,tilt")
else
    FAIL+=("info sequence: got '$INFO'")
fi

# bubble right, home, left
for LED in "7 4 15" "4 4 15" "0 4 15"; do
    check "$OUT/pd.log" "^tled: $LED\$" "bubble LED $LED"
done
# cross + energy bar (m=50 -> h=5 -> rows 2..7)
check "$OUT/pd.log" "^tled: 3 3 2\$" "cross dot 3 3 2"
check "$OUT/pd.log" "^tled: 7 7 8\$" "energy bar cell 7 7 8"
check "$OUT/pd.log" "^tled: 7 2 8\$" "energy bar cell 7 2 8"

echo "---- results"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
