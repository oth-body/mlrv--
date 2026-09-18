#!/usr/bin/env bash
# Verifies play_loop~ against real loaded audio content, not silence.
#
# Generates a deterministic linear-ramp WAV (gen_test_wav.py), loads it into
# play_loop~ via soundfiler, plays one full loop cycle, captures the output
# via tabwrite~, writes it back to a WAV, and checks it against the known
# expected ramp: correlation coefficient, mean absolute error, and strict
# monotonicity across every sample. A real bug was caught this way once
# already (a hardcoded samplerate creation arg that didn't match Pd's
# actual engine rate) -- this script exists so that class of bug gets
# caught automatically next time, not by chance during a manual test.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-audio-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/ramp.wav" "$OUT/captured.wav"

N=4410
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/ramp.wav" "$N" || exit 1

# test_play_loop_audio.pd hardcodes these paths -- keep in sync.
cp "$OUT/ramp.wav" /tmp/mlrv_ramp_test.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_play_loop_audio.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_captured.wav "$OUT/captured.wav" 2>/dev/null

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/captured.wav" "$N" <<'EOF'
import sys, wave, struct, math

path, n = sys.argv[1], int(sys.argv[2])
try:
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        captured = struct.unpack("<" + str(w.getnframes()) + "h", data)
except FileNotFoundError:
    print("FAIL captured.wav was not written")
    sys.exit(1)

if len(captured) != n:
    print(f"FAIL captured.wav has {len(captured)} samples, expected {n}")
    sys.exit(1)

expected = [(-16000 + 32000 * i / (n - 1)) / 32768.0 for i in range(n)]
got = [v / 32768.0 for v in captured]

mean_err = sum(abs(c - e) for c, e in zip(got, expected)) / n
increasing = sum(1 for i in range(1, n) if got[i] >= got[i - 1] - 1e-4)

mc = sum(got) / n
me = sum(expected) / n
cov = sum((c - mc) * (e - me) for c, e in zip(got, expected))
sc = math.sqrt(sum((c - mc) ** 2 for c in got))
se = math.sqrt(sum((e - me) ** 2 for e in expected))
corr = cov / (sc * se) if sc and se else 0.0

print(f"PASS mean abs error {mean_err*100:.3f}% of full-scale" if mean_err < 0.01
      else f"FAIL mean abs error {mean_err*100:.3f}% of full-scale (want < 1%)")
print(f"PASS monotonic {increasing}/{n-1} steps" if increasing == n - 1
      else f"FAIL monotonic only {increasing}/{n-1} steps")
print(f"PASS correlation {corr:.6f}" if corr > 0.999
      else f"FAIL correlation only {corr:.6f} (want > 0.999)")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("audio content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
