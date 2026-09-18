#!/usr/bin/env bash
# Verifies mixer.pd `query`: tracked vol/send state dumped as replayable
# control lines. Control-only, no audio fixtures.
#
# Timeline (test_mixer_query.pd):
#   query (defaults) -> vol 0..3 = 1, send 0..3 = 0
#   vol/send sets + out-of-range vol 9 (ignored, no error)
#   query -> updated values, all 8 lines exact and ascending
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-mix-query-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_mixer_query.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()

if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

EXPECTED="vol 0 1|vol 1 1|vol 2 1|vol 3 1|send 0 0|send 1 0|send 2 0|send 3 0|vol 0 0.5|vol 1 1|vol 2 0.25|vol 3 1|send 0 0|send 1 0.5|send 2 0|send 3 0.125"
GOT="$(grep -o '^q: [a-z]* [0-9]* [0-9.]*' "$OUT/pd.log" | sed 's/^q: //' | tr '\n' '|' | sed 's/|$//')"
if [ "$GOT" = "$EXPECTED" ]; then
    PASS+=("exact query sequence (defaults + updated)")
else
    FAIL+=("query sequence mismatch: got '$GOT'")
fi

if grep -q 'vol 9\|send 9' "$OUT/pd.log"; then
    FAIL+=("out-of-range vol 9 produced no report")
else
    PASS+=("out-of-range vol 9 produced no report")
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
