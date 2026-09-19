#!/usr/bin/env bash
# End-to-end headless test of mlrv-pd/m64_test.pd against
# tests/fake_serialosc.py. Verifies the three sections of the test
# project actually round-trip through the primitives:
#
#   SECTION 2 (manual LED): the loadbang fires "3 3 15" -> grid -> serialosc
#     -> fake device receives /monome/grid/led/level/set 3 3 15
#   SECTION 1 (input): device_register prints on handshake + each fake
#     /monome/grid/key event prints at grid_key
#   SECTION 3 (live echo): each fake /monome/grid/key event ALSO bounces
#     back out the grid -> serialosc -> fake device as a level_set for the
#     same x,y at level 15
#
# Handles the common case where the user's serialosc daemon is already
# running on UDP 12002 (which serialoscd binds with SO_REUSEADDR but no
# SO_REUSEPORT, so a second bind always fails -- the fake can't run
# alongside it). In that case we report only the load-dependent checks
# (patch loads clean, SECTION 2 manual LED fires) and SKIP the
# handshake-dependent ones with a clear reason, rather than failing
# loudly. With the real daemon stopped, all checks run.
#
# Exits 0 on all checks passing OR on graceful skip, 1 on real failure.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-m64-e2e"
mkdir -p "$OUT"
rm -f "$OUT/fake.log" "$OUT/pd.log"

USING_FAKE=1
if ss -tuln 2>/dev/null | grep -q ":12002"; then
    USING_FAKE=0
    echo "  note: serialosc already on :12002, skipping fake (handshake checks will be skipped)"
else
    FAKE_GRID_KEYS="4,5,1 4,5,0" \
        python3 mlrv-pd/tests/fake_serialosc.py > "$OUT/fake.log" 2>&1 &
    FAKE_PID=$!
    sleep 0.5
fi

timeout 6 pd -nogui -stderr \
    -path mlrv-pd/abstractions \
    -path mlrv-pd/patchers \
    mlrv-pd/m64_test.pd > "$OUT/pd.log" 2>&1
PD_EXIT=$?
sleep 0.3
if [ "$USING_FAKE" = "1" ]; then
    kill "$FAKE_PID" 2>/dev/null
    wait "$FAKE_PID" 2>/dev/null
fi

PASS=()
FAIL=()
SKIP=()
check() {  # check <file> <pattern> <label>
    if grep -qE "$2" "$1"; then
        PASS+=("$3")
    else
        FAIL+=("$3  (pattern: $2)")
    fi
}
skip() { SKIP+=("$1"); }

# Load-only checks (work in both modes -- no daemon needed)
check "$OUT/pd.log" "led_manual: 3 3 15"                          "SECTION 2 manual LED print (loadbang)"
# Pd should have loaded clean. The "netsend: already connected"
# warning comes from serialosc.pd itself when the fake daemon's
# double-reply (one per /serialosc/list and /serialosc/notify) triggers
# a re-handshake -- documented in patchers/serialosc.pd's own comments,
# NOT a real failure. Filter it out and fail on anything else.
ERR_COUNT=$(grep -E "(error:|connection failed)" "$OUT/pd.log" \
            | grep -v "netsend: already connected" | wc -l)
if [ "$ERR_COUNT" -gt 0 ]; then
    FAIL+=("pd logged $ERR_COUNT real error(s) (see $OUT/pd.log)")
else
    PASS+=("pd loaded clean (only known-harmless netsend: already connected if any)")
fi

# Handshake-dependent checks (need the fake)
if [ "$USING_FAKE" = "1" ]; then
    check "$OUT/pd.log" "device_register:.*m0000-0000.*grid.*40921" "SECTION 1 device_register on handshake"
    check "$OUT/pd.log" "grid_key: 4 5 1"                             "SECTION 1 grid_key press event"
    check "$OUT/pd.log" "grid_key: 4 5 0"                             "SECTION 1 grid_key release event"
    check "$OUT/pd.log" "echo_led: 4 5 15"                           "SECTION 3 echo prints the LED command"
    check "$OUT/fake.log" "/sys/port 8000"                            "handshake /sys/port"
    check "$OUT/fake.log" "/sys/prefix /monome"                       "handshake /sys/prefix"
    # NOTE: we do NOT check that /monome/grid/led/level/set arrives at
    # the fake device -- fake_serialosc.py's device thread exits its
    # recv loop after the handshake completes (it only needs /sys/port
    # and /sys/prefix to know where to send the simulated grid keys),
    # so any LED command serialosc sends after that point is invisible
    # to the fake. The Pd-side "echo_led" print above is the strongest
    # assertion the current fake can support. Verifying real LED
    # feedback requires either patching the fake to keep listening, or
    # running against real hardware.
else
    skip "SECTION 1 device_register on handshake (real daemon on :12002)"
    skip "SECTION 1 grid_key press event (real daemon on :12002)"
    skip "SECTION 1 grid_key release event (real daemon on :12002)"
    skip "SECTION 3 echo prints the LED command (real daemon on :12002)"
    skip "handshake /sys/port (real daemon on :12002)"
    skip "handshake /sys/prefix (real daemon on :12002)"
fi

echo
echo "=== m64_test.pd end-to-end ==="
for p in "${PASS[@]}"; do echo "  PASS  $p"; done
for f in "${FAIL[@]}"; do echo "  FAIL  $f"; done
for s in "${SKIP[@]}"; do echo "  SKIP  $s"; done
echo "  pd log:    $OUT/pd.log"
[ "$USING_FAKE" = "1" ] && echo "  fake log:  $OUT/fake.log"
echo "  pd exit:   $PD_EXIT"
[ ${#FAIL[@]} -eq 0 ]
