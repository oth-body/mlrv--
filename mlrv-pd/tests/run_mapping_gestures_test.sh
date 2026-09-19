#!/usr/bin/env bash
# Verifies mapping.pd's grid gestures (user-picked direct-rows layout):
# y=6 buttons + LED flash/clear, y=5 group cycle + wrap, y=4 slave toggle
# proved behaviorally (held then immediate trigger timing). Timeline in
# test_mapping_gestures.pd (builders/build_test_mapping_gestures.py).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-mapgest-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 8 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mapping_gestures.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
ok()  { PASS+=("$1"); }
bad() { FAIL+=("$1"); }

if grep -qi "error:" "$OUT/pd.log"; then bad "no pd errors"; else ok "no pd errors"; fi

[ "$(grep -c '^mctrl: groupstop 3$' "$OUT/pd.log")" = 1 ] && ok "y6: groupstop 3 exactly once" || bad "groupstop"
LED6="$(grep -o '^led: 2 6 [01]5\?' "$OUT/pd.log" | tr '\n' '|')"
[ "$LED6" = "led: 2 6 15|led: 2 6 0|" ] && ok "y6: LED flash then release-clear" || bad "y6 LED: '$LED6'"
PAT="$(grep -o '^pat: .*' "$OUT/pd.log" | sed 's/^pat: //' | tr '\n' '|')"
[ "$PAT" = "arm|play|stop|" ] && ok "y6: pattern arm/play/stop on outlet 3" || bad "pattern outlet: '$PAT'"
[ "$(grep -c '^rec: record$' "$OUT/pd.log")" = 1 ] && ok "y6: record on outlet 4" || bad "record outlet"
GRP="$(grep -o '^mctrl: group 2 .*$' "$OUT/pd.log" | sed 's/^mctrl: //' | tr '\n' '|')"
[ "$GRP" = "group 2 1|group 2 2|group 2 3|group 2 4|group 2 0|" ] && ok "y5: group cycles 1-4 then wraps to 0" || bad "group cycle: '$GRP'"
GLED="$(grep -o '^led: 2 5 .*$' "$OUT/pd.log" | sed 's/^led: //' | tr '\n' '|')"
[ "$GLED" = "2 5 3|2 5 6|2 5 9|2 5 12|2 5 0|" ] && ok "y5: LED readout tracks group" || bad "group LED: '$GLED'"
SLED="$(grep -o '^led: 3 4 .*$' "$OUT/pd.log" | sed 's/^led: //' | tr '\n' '|')"
[ "$SLED" = "3 4 15|3 4 0|" ] && ok "y4: slave LED on then off" || bad "slave LED: '$SLED'"
mapfile -t PT < <(grep '^play_ms:' "$OUT/pd.log" | awk '{print $2}' | cut -d. -f1)
if [ "${#PT[@]}" = 2 ] && [ "${PT[0]}" -ge 260 ] && [ "${PT[0]}" -le 300 ] && [ "${PT[1]}" -lt 100 ]; then
    ok "y4: slaved trigger held ~280ms (${PT[0]}), un-slaved immediate (${PT[1]})"
else
    bad "slave timing: '${PT[*]}' (want 260-300 then <100)"
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
