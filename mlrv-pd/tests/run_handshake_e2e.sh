#!/usr/bin/env bash
# End-to-end headless test of mlrv-pd/patchers/serialosc.pd against a fake
# serialosc daemon + fake grid device (tests/fake_serialosc.py).
#
# Verifies the full loop that could not be tested with real hardware:
#   discovery (list+notify) -> /serialosc/device reply -> handshake
#   (connect, /sys/port, /sys/prefix) -> /monome/grid/key round trip back
#   into the patch and out the grid-key outlet.
#
# Exit 0 on all checks passing, 1 otherwise. Prints a per-check summary.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-e2e"
mkdir -p "$OUT"
rm -f "$OUT/fake.log" "$OUT/pd.log"

python3 mlrv-pd/tests/fake_serialosc.py > "$OUT/fake.log" 2>&1 &
FAKE_PID=$!
sleep 0.5   # let the fake daemon bind 12002 before pd's loadbang announces

timeout 6 pd -nogui -stderr -path mlrv-pd/patchers \
    mlrv-pd/tests/test_serialosc_handshake.pd > "$OUT/pd.log" 2>&1
sleep 0.3
kill "$FAKE_PID" 2>/dev/null
wait "$FAKE_PID" 2>/dev/null

PASS=()
FAIL=()
check() {  # check <file> <pattern> <label>
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}

check "$OUT/fake.log" "DAEMON /serialosc/list"          "discovery: /serialosc/list to daemon"
check "$OUT/fake.log" "DAEMON /serialosc/notify"        "discovery: /serialosc/notify to daemon"
check "$OUT/fake.log" "DEVICE /sys/port 8000"           "handshake: /sys/port 8000 at device"
check "$OUT/fake.log" "DEVICE /sys/prefix /monome"      "handshake: /sys/prefix /monome at device"
check "$OUT/fake.log" "DEVICE sent /monome/grid/key 2 3 1" "device: grid key 2 3 1 sent back"
check "$OUT/pd.log"   "device_register: m0000-0000 grid 40921" "pd: device register triple out outlet 0"
check "$OUT/pd.log"   "grid_key: 2 3 1"                  "pd: grid key round-tripped out outlet 1"

echo "---- fake serialosc log ($OUT/fake.log)"
cat "$OUT/fake.log"
echo "---- pd log ($OUT/pd.log)"
cat "$OUT/pd.log"
echo "---- results"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done
[ "${#FAIL[@]}" -eq 0 ]