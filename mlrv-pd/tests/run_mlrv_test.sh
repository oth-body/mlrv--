#!/usr/bin/env bash
# End-to-end regression for mlrv.pd, the top-level instrument. No real
# hardware and no listening required: runs the whole chain (serialosc ->
# mapping -> file_poly -> master, with the LED path back through grid ->
# serialosc) against tests/fake_serialosc.py (a fake daemon + fake grid
# device), simulating a press/release at mapping.pd's trigger row for
# slot 0 via FAKE_GRID_KEYS. Verifies real, correctly-scaled captured
# audio AND the LED command sent back for the pressed cell -- both
# outputs of the full integration, not just a clean load.
#
# test_mlrv.pd shares its core wiring with the real mlrv.pd via
# mlrv-pd/tests/builders/mlrv_core.py, so this is testing the actual
# production wiring, not a hand-copied approximation that could drift.
#
# Requires port 12002 free -- if the real serialosc daemon is running,
# stop it first (this suite will otherwise silently talk to the real
# grid instead of the fake fixture, and likely fail or give misleading
# results since the real device won't have this fixture's expected
# content loaded).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

if ss -uln 2>/dev/null | grep -q ':12002 '; then
    echo "FAIL port 12002 already in use (real serialosc daemon running?) -- stop it first"
    exit 1
fi

OUT="${TMPDIR:-/tmp}/mlrv-e2e-test"
mkdir -p "$OUT"
rm -f "$OUT"/*.wav "$OUT/pd.log" "$OUT/fake.log" \
      /tmp/mlrv_e2e_src.wav /tmp/mlrv_e2e_cap.wav

N=4410
PEAK=16000
GAIN=0.8
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/src.wav" "$N" ramp "$PEAK" || exit 1

# test_mlrv.pd hardcodes this path -- keep in sync.
cp "$OUT/src.wav" /tmp/mlrv_e2e_src.wav

FAKE_GRID_KEYS="0,7,1 0,7,0" python3 mlrv-pd/tests/fake_serialosc.py \
    > "$OUT/fake.log" 2>&1 &
FAKE_PID=$!
sleep 0.5

timeout 4 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mlrv.pd > "$OUT/pd.log" 2>&1
sleep 0.3
kill "$FAKE_PID" 2>/dev/null
wait "$FAKE_PID" 2>/dev/null
cp /tmp/mlrv_e2e_cap.wav "$OUT/cap.wav" 2>/dev/null

PASS=()
FAIL=()

# every error line except the known, documented double-handshake cosmetic
# issue (serialosc.pd's rescan replies twice; harmless, see CLAUDE.md and
# handoff log) counts as a real failure.
UNEXPECTED_ERRORS="$(grep -i 'error:' "$OUT/pd.log" | grep -v 'netsend: already connected')"
if [ -z "$UNEXPECTED_ERRORS" ]; then
    PASS+=("no unexpected pd errors")
else
    FAIL+=("no unexpected pd errors")
    echo "$UNEXPECTED_ERRORS"
fi

check() {  # check <file> <pattern> <label>
    if grep -q -- "$2" "$1"; then PASS+=("$3"); else FAIL+=("$3"); fi
}
check "$OUT/fake.log" "DAEMON /serialosc/list" "discovery reached the fake daemon"
check "$OUT/pd.log"   "mlrv_e2e_led: 0 7 15"   "LED feedback: trigger cell 0,7 lit full (15)"

if [ -s "$OUT/cap.wav" ]; then PASS+=("audio capture written"); else FAIL+=("audio capture written"); fi

PYOUT="$(python3 - "$OUT/cap.wav" "$PEAK" "$GAIN" <<'EOF'
import math, struct, sys, wave

path, peak, gain = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
try:
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        got = struct.unpack("<" + str(w.getnframes()) + "h", data)
except FileNotFoundError:
    print("FAIL captured audio: file not found")
    sys.exit(0)

# expected: raw ramp peak -> normalized -> master gain -> tanh(x*1.2) soft-clip
norm_peak = peak / 32768.0
expected = math.tanh(norm_peak * gain * 1.2) * 32768.0

pk = max(abs(x) for x in got)
tol = 400  # generous: capture window lands at an arbitrary loop phase, not
           # necessarily the exact peak sample, plus tanh/interpolation
good = abs(pk - expected) <= tol
print((f"PASS captured audio peak {pk} matches expected {expected:.1f} "
       f"(gain {gain} + tanh soft-clip), tol {tol}") if good else
      (f"FAIL captured audio peak {pk}, expected {expected:.1f} +/- {tol}"))

# sanity: must be genuinely non-silent -- rules out "test passed because
# everything is near-zero and happens to be within a loose tolerance"
good2 = pk > 5000
print(f"PASS captured audio clearly non-silent (peak {pk} > 5000)" if good2
      else f"FAIL captured audio too quiet (peak {pk})")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q '^FAIL'; then FAIL+=("audio content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
