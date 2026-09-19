#!/usr/bin/env bash
# End-to-end test of the pong demo against a fake serialosc daemon + fake
# grid (tests/pong_e2e.py): handshake, scripted key presses into the real
# serialosc.pd -> pong -> grid chain, and LED triples back at the device.
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-pong-e2e"
mkdir -p "$OUT"
rm -f "$OUT/fake.log" "$OUT/pd.log"

python3 mlrv-pd/tests/pong_e2e.py > "$OUT/fake.log" 2>&1 &
FAKE_PID=$!
sleep 0.5

timeout 9 pd -nogui -stderr -path mlrv-pd/patchers \
    mlrv-pd/pong_demo.pd > "$OUT/pd.log" 2>&1
sleep 0.3
kill "$FAKE_PID" 2>/dev/null
wait "$FAKE_PID" 2>/dev/null

PASS=()
FAIL=()
check() {
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}

# known-benign only: the fake daemon answers list AND notify separately, so the
# handshake runs twice ("netsend: already connected", documented in
# serialosc.pd). fail on any OTHER error.
if grep -qi "error:" "$OUT/pd.log"; then
    if grep -qi -v "already connected" <(grep -i "error:" "$OUT/pd.log"); then
        FAIL+=("no unexpected pd errors")
    else
        PASS+=("no unexpected pd errors (only benign double-handshake)")
    fi
else
    PASS+=("no pd errors at all")
fi
check "$OUT/fake.log" "DAEMON /serialosc/list"            "discovery: list reaches daemon"
check "$OUT/fake.log" "DEVICE /sys/port 8000"             "handshake: /sys/port 8000"
check "$OUT/fake.log" "DEVICE /sys/prefix /monome"        "handshake: /sys/prefix /monome"
check "$OUT/fake.log" "sent /monome/grid/key 0 3 1"       "device: key press sent"
check "$OUT/fake.log" "got /monome/grid/led/level/set"    "led: level/set reaches device"
# Pd sends int-valued floats, logged raw: "0.0 3.0 10.0"
check "$OUT/fake.log" "got /monome/grid/led/level/set 0.0 3.0 10.0" "led: left-paddle press lit (0 3)"
check "$OUT/fake.log" "got /monome/grid/led/level/set .* .* 15.0" "led: ball (level 15) drawn"

echo "---- fake log ($OUT/fake.log, led lines sampled)"
grep -c "got /monome/grid/led/level/set" "$OUT/fake.log" | xargs echo "led msgs total:"
grep "got /monome/grid/led/level/set" "$OUT/fake.log" | sort | uniq -c | sort -rn | head -12
echo "---- pd log tail ($OUT/pd.log)"
tail -8 "$OUT/pd.log"
echo "---- results"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
