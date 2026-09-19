#!/usr/bin/env bash
# Verifies pattern_recorder.pd's full record -> auto-stop -> playback ->
# loop -> stop cycle against real elapsed time and real event content,
# not just message order or a clean load.
#
# Scenario: arm, record two live events 100ms apart (length=300ms),
# confirm both pass through live immediately, confirm auto-stop starts
# playback at the correct absolute time (300ms length + 100ms event1
# offset = 400ms), confirm playback content and relative timing match
# what was recorded, confirm seamless looping (a new lap's first event
# lands at the exact same instant as the previous lap's last event --
# qlist's done-bang fires with no built-in gap), and confirm `stop`
# halts further playback immediately rather than finishing the lap.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-pattern-recorder-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 3 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_pattern_recorder.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

check() {  # check <label> <pattern>
    if grep -q -- "$2" "$OUT/pd.log"; then PASS+=("$1"); else FAIL+=("$1"); fi
}

check "live event 1 passes through immediately" "^live: 2 3 1$"
check "live event 2 passes through immediately" "^live: 4 5 0$"

# exactly 5 playback events fire before stop (lap1: 2, lap2 event1, lap2 event2, lap3 event1 -- then stop)
COUNT="$(grep -c "^playback:" "$OUT/pd.log")"
if [ "$COUNT" -eq 5 ]; then
    PASS+=("exactly 5 playback events fired before stop (got $COUNT)")
else
    FAIL+=("exactly 5 playback events fired before stop (got $COUNT, want 5)")
fi

# content + order: 2 3 1, 4 5 0, 2 3 1, 4 5 0, 2 3 1
mapfile -t EVENTS < <(grep "^playback:" "$OUT/pd.log" | sed 's/^playback: //')
EXPECTED=("2 3 1" "4 5 0" "2 3 1" "4 5 0" "2 3 1")
CONTENT_OK=1
for i in 0 1 2 3 4; do
    if [ "${EVENTS[$i]:-}" != "${EXPECTED[$i]}" ]; then CONTENT_OK=0; fi
done
if [ "$CONTENT_OK" -eq 1 ]; then
    PASS+=("playback content and order match recorded events exactly")
else
    FAIL+=("playback content and order match recorded events exactly (got: ${EVENTS[*]:-none})")
fi

# timing: first playback event at 400ms (300 length + 100 event1 offset)
mapfile -t TIMES < <(grep "^elapsed_since_load:" "$OUT/pd.log" | sed 's/^elapsed_since_load: //')
if [ "${TIMES[0]:-}" = "400" ]; then
    PASS+=("first playback event fires at exactly 400ms (300 length + 100 offset)")
else
    FAIL+=("first playback event fires at exactly 400ms (got ${TIMES[0]:-none})")
fi

# timing: lap1's two events are 100ms apart (400, 500), matching the recorded gap
if [ "${TIMES[1]:-}" = "500" ]; then
    PASS+=("lap1's second event fires 100ms after the first (500ms, matches recorded gap)")
else
    FAIL+=("lap1's second event at 500ms (got ${TIMES[1]:-none})")
fi

# timing: seamless loop -- lap2's first event lands at the SAME instant as lap1's last (500, 500)
if [ "${TIMES[2]:-}" = "500" ]; then
    PASS+=("loop is seamless: lap2 starts at the same instant lap1 ended (500ms)")
else
    FAIL+=("loop is seamless: lap2 starts at 500ms (got ${TIMES[2]:-none})")
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
