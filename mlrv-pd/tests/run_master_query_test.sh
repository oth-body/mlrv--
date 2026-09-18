#!/usr/bin/env bash
# Verifies master.pd `query`: tracked gain dumped as a bare float, directly
# replayable into the gain inlet. Control-only, no audio fixtures.
#
# Timeline (test_master_query.pd):
#   query (default 0) -> set 0.8 -> query -> set 0.5 -> query
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-master-query-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_master_query.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()

if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

EXPECTED="0|0.8|0.5"
GOT="$(grep -o '^q: [0-9.]*' "$OUT/pd.log" | sed 's/^q: //' | tr '\n' '|' | sed 's/|$//')"
if [ "$GOT" = "$EXPECTED" ]; then
    PASS+=("exact query sequence (0, 0.8, 0.5)")
else
    FAIL+=("query sequence mismatch: got '$GOT'")
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
