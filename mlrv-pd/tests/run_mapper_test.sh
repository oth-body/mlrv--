#!/usr/bin/env bash
# Verifies mapper.pd's binding core (1:1 mlrv recreation, item 5,
# increment 1): learn/bind/steal/dispatch/min-edit/clear across all four
# param kinds, asserting exact dispatch bytes. Timeline lives in
# test_mapper.pd (built by builders/build_test_mapper.py).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-mapper-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 8 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_mapper.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
ok()  { PASS+=("$1"); }
bad() { FAIL+=("$1"); }

if grep -qi "error:" "$OUT/pd.log"; then bad "no pd errors"; else ok "no pd errors"; fi

# --- learn/bind reports, in order ---
LEARN="$(grep -o '^learning: .*' "$OUT/pd.log" | sed 's/^learning: //' | tr '\n' '|')"
[ "$LEARN" = "0|1|4|6|5|3|" ] && ok "learn sequence 0,1,4,6,5,3" || bad "learn sequence: '$LEARN'"
BOUND="$(grep -o '^bound: .*' "$OUT/pd.log" | sed 's/^bound: //' | tr '\n' '|')"
[ "$BOUND" = "0 16|1 16|4 131|6 261|5 20|3 30|" ] && ok "bind reports exact" || bad "bind reports: '$BOUND'"

# --- dispatch bytes ---
T="$(grep -o '^t_tempo: .*' "$OUT/pd.log" | sed 's/^t_tempo: //' | tr '\n' '|')"
[ "$T" = "90|140|" ] && ok "tempo scaled 90 then 140 (min-edit applies)" || bad "tempo dispatch: '$T'"
M="$(grep -o '^t_master: .*' "$OUT/pd.log" | sed 's/^t_master: //' | tr '\n' '|')"
[ "$M" = "1.5|" ] && ok "steal works: master once, tempo silent, clear silent" || bad "master dispatch: '$M'"
[ "$(grep -c '^t_master:' "$OUT/pd.log")" = 1 ] && ok "clear works: no dispatch after clear" || bad "clear failed"
G="$(grep -o '^t_gain: .*' "$OUT/pd.log" | sed 's/^t_gain: //' | tr '\n' '|')"
[ "$G" = "1 1|" ] && ok "vgain1 -> gain 1 1" || bad "gain dispatch: '$G'"
MO="$(grep -o '^t_mode: .*' "$OUT/pd.log" | sed 's/^t_mode: //' | tr '\n' '|')"
[ "$MO" = "1 shot|1 loop|" ] && ok "dsym -> mode 1 shot/loop" || bad "mode dispatch: '$MO'"
[ "$(grep -c '^t_groupstop: 1$' "$OUT/pd.log")" = 1 ] && ok "trig -> groupstop 1" || bad "groupstop dispatch"
GR="$(grep -o '^t_group: .*' "$OUT/pd.log" | sed 's/^t_group: //' | tr '\n' '|')"
[ "$GR" = "0 2|0 4|" ] && ok "dint scaled+rounded, clamp at max" || bad "group dispatch: '$GR'"
[ "$(grep -c '^t_vol:' "$OUT/pd.log")" = 0 ] && ok "unbound ctl dropped silently" || bad "unbound ctl leaked"

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
