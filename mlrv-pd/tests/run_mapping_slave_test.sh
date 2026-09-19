#!/usr/bin/env bash
# Verifies mapping.pd's slave wiring (1:1 mlrv recreation, item 2) against
# real elapsed time (Pd's own [timer]), not just message order:
# slaved press -> LED immediate + play held to the quantize grid (default
# 120bpm/1 beat = 500ms; press at 220ms -> release ~280ms later, mirroring
# run_clock_test.sh's numbers); unslaved -> immediate; un-slave and
# out-of-range slave -> immediate; tempo/quantize forwarded into the
# contained clock (steady-state beat-pulse intervals 250/500ms).
# Timeline lives in test_mapping_slave.pd (built by
# builders/build_test_mapping_slave.py).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-mapslave-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 12 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mapping_slave.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
ok()  { PASS+=("$1"); }
bad() { FAIL+=("$1"); }

if grep -qi "error:" "$OUT/pd.log"; then bad "no pd errors"; else ok "no pd errors"; fi

# --- exact held + immediate play messages (byte-identical rebuild) ---
N_HELD="$(grep -c '^mctrl: play 0 1 0 4410$' "$OUT/pd.log")"
N_S1="$(grep -c '^mctrl: play 1 1 0 4410$' "$OUT/pd.log")"
if [ "$N_HELD" = 3 ] && [ "$N_S1" = 1 ]; then
    ok "4 plays exactly: 3x slot0 + 1x slot1, all byte-exact"
else
    bad "plays: want 3x slot0 + 1x slot1, got ${N_HELD}x + ${N_S1}x"
fi

# --- release timing, in trigger order: held ~280, then 3x immediate ---
mapfile -t PT < <(grep '^play_ms:' "$OUT/pd.log" | awk '{print $2}' | cut -d. -f1)
if [ "${#PT[@]}" = 4 ] && [ "${PT[0]}" -ge 260 ] && [ "${PT[0]}" -le 300 ] \
    && [ "${PT[1]}" -lt 100 ] && [ "${PT[2]}" -lt 100 ] && [ "${PT[3]}" -lt 100 ]; then
    ok "slaved release ~280ms (${PT[0]}), 3x unslaved immediate (${PT[1]},${PT[2]},${PT[3]})"
else
    bad "play timing: got '${PT[*]}' (want 260-300 then 3x <100)"
fi

# --- LED always immediate (press ack, even for slaved slots) ---
if grep '^led_ms:' "$OUT/pd.log" | awk '{print $2}' | cut -d. -f1 | \
    awk '{if ($1 >= 100) bad=1} END {exit bad}'; then
    ok "all 4 LEDs immediate (<100ms)"
else
    bad "LED timing: some led_ms >= 100"
fi
if [ "$(grep -c '^led: 0 7 15$' "$OUT/pd.log")" = 3 ] \
    && [ "$(grep -c '^led: 1 7 15$' "$OUT/pd.log")" = 1 ]; then
    ok "LED content exact (3x 0 7 15, 1x 1 7 15)"
else
    bad "LED content wrong"
fi

# --- tempo/quantize forwarding: steady-state beat intervals ---
# (first report per timer is startup garbage -- see builder -- skip it)
if grep '^int1_ms:' "$OUT/pd.log" | tail -n +2 | head -3 | awk '{print $2}' | cut -d. -f1 | \
    awk '{if ($1 < 175 || $1 > 325) bad=1} END {exit bad}'; then
    ok "tempo 240 forwarded: 3x ~250ms beat intervals"
else
    bad "tempo phase intervals wrong: $(grep '^int1_ms:' "$OUT/pd.log" | tail -n +2 | head -3 | tr '\n' ' ')"
fi
if grep '^int2_ms:' "$OUT/pd.log" | tail -n +2 | head -3 | awk '{print $2}' | cut -d. -f1 | \
    awk '{if ($1 < 400 || $1 > 600) bad=1} END {exit bad}'; then
    ok "quantize 2 forwarded: 3x ~500ms beat intervals"
else
    bad "quantize phase intervals wrong: $(grep '^int2_ms:' "$OUT/pd.log" | tail -n +2 | head -3 | tr '\n' ' ')"
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
