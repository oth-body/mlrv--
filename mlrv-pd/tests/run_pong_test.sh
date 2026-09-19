#!/usr/bin/env bash
# Deterministic logic test for mlrv-pd/patchers/pong.pd: scripted presses +
# deterministic serve/tick (no hardware, metro effectively off). Timeline in
# tests/builders/build_test_pong.py; expected pinfo sequence exactly:
#   reset | score 0 0 | score 1 0 | score 1 1 | reset | score 0 0
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-pong-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 6 pd -nogui -stderr -path mlrv-pd/patchers \
    mlrv-pd/tests/test_pong.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check() {
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}

if grep -qiE "error:|connection failed|no such object" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

# --- info sequence exactly ---
INFO="$(grep -o '^pinfo: .*' "$OUT/pd.log" | sed 's/^pinfo: //' | tr '\n' '|')"
# rally 1 misses the right paddle -> SR=1 : "score 0 1"
# rally 2 misses the left paddle  -> SL=1 : "score 1 1"
EXPECT_INFO="reset|score 0 0|reset|score 0 0|score 0 1|score 1 1|reset|score 0 0|"
if [ "$INFO" = "$EXPECT_INFO" ]; then
    PASS+=("info sequence exactly: load,reset,0-1,1-1,reset")
else
    FAIL+=("info sequence: got '$INFO'")
fi

# --- paddle LEDs: LP=3 then LP=1, RP=1 ---
for LED in "0 2 10" "0 3 10" "0 4 10" "0 0 10" "0 1 10" \
           "7 0 10" "7 1 10" "7 2 10"; do
    check "$OUT/pd.log" "^pled: $LED\$" "paddle LED $LED"
done

# --- net dots use grayscale level 2 ---
check "$OUT/pd.log" "^pled: 3 0 2\$" "net dot 3 0 2"
check "$OUT/pd.log" "^pled: 4 6 2\$" "net dot 4 6 2"

# --- ball sweep + trail: first rally moves 4->5->6 at row 3 ---
for LED in "4 3 15" "5 3 15" "6 3 15"; do
    check "$OUT/pd.log" "^pled: $LED\$" "ball LED $LED"
done
check "$OUT/pd.log" "^pled: 5 3 4\$" "trail LED 5 3 4"

# --- after the miss the ball respawns at 3 3 (post-spawn render) ---
check "$OUT/pd.log" "^pled: 3 3 15\$" "respawn ball 3 3 15"

echo "---- pd log ($OUT/pd.log)"
cat "$OUT/pd.log"
echo "---- results"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
