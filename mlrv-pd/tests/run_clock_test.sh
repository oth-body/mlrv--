#!/usr/bin/env bash
# Verifies clock.pd's quantize-gate mechanism against real elapsed time
# (Pd's own [timer]), not just message-arrival order or a clean load.
# Default state: 120bpm + quantize 1 beat = 500ms grid. A trigger fired
# 220ms after load must be released at the next grid boundary (500ms),
# i.e. ~280ms after the trigger itself -- not immediately.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-clock-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 3 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_clock.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

if grep -q "^released: bang$" "$OUT/pd.log"; then
    PASS+=("trigger was released (quantize gate fired)")
else
    FAIL+=("trigger was released (quantize gate fired)")
fi

ELAPSED="$(grep "^elapsed_ms:" "$OUT/pd.log" | tail -1 | awk '{print $2}')"
if [ -n "$ELAPSED" ] && [ "$ELAPSED" -ge 260 ] && [ "$ELAPSED" -le 300 ]; then
    PASS+=("released ~280ms after trigger (held to the 500ms grid boundary, got ${ELAPSED}ms)")
else
    FAIL+=("released ~280ms after trigger, got '${ELAPSED}ms' (want 260-300ms)")
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
