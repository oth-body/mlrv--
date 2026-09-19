#!/usr/bin/env bash
# Verifies play_loop~ actually plays BACKWARD when given a negative rate --
# not just that phasor~ handles a negative frequency in isolation (probed
# separately, see the Per-Voice Sample Parameters handoff note), but that
# the real abstraction, reading a real loaded array through its real
# rate/loopEnd/loopStart control inlet, produces a real reversed reading of
# real audio content.
#
# Mirrors run_play_loop_audio_test.sh's fixture/capture approach exactly,
# with one deliberate difference in the expected trace: with the loop
# region reset to phase 0 (the abstraction's existing, unmodified retrigger
# behavior) and a negative rate applied, phasor~ decrements below 0 and
# wraps to just-under-1 on the *next* sample -- confirmed by a direct
# tabwrite~ sample-level probe before this test was written (phase[0]=0,
# phase[1]=0.999792 at freq -10Hz/48000sr). That means captured sample 0
# is a one-sample artifact (reads the loop-start value, not loop-end) and
# every following sample is a clean, continuous descending ramp. The
# expected trace below is built with that one-sample offset baked in
# analytically, not discovered by curve-fitting the actual output.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-audio-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/ramp.wav" "$OUT/captured.wav"

N=4410
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/ramp.wav" "$N" || exit 1

# test_play_loop_reverse.pd hardcodes this path -- keep in sync.
cp "$OUT/ramp.wav" /tmp/mlrv_ramp_test.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_play_loop_reverse.pd > "$OUT/pd.log" 2>&1
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

def ramp_value(idx):
    # same formula as gen_test_wav.py's ramp mode
    return (-16000 + 32000 * idx / (n - 1)) / 32768.0

# sample 0: the one-sample reset artifact (reads loop-start, idx 0)
# samples 1..n-1: read idx = n - i (continuous descent from near the top)
expected = [ramp_value(0)] + [ramp_value(n - i) for i in range(1, n)]
got = [v / 32768.0 for v in captured]

# exclude index 0 from error/monotonicity stats -- it's a known, expected
# single-sample artifact of the retrigger-then-negative-rate mechanism,
# not something the abstraction is meant to smooth over.
mean_err = sum(abs(c - e) for c, e in zip(got[1:], expected[1:])) / (n - 1)
decreasing = sum(1 for i in range(2, n) if got[i] <= got[i - 1] + 1e-4)

mc = sum(got[1:]) / (n - 1)
me = sum(expected[1:]) / (n - 1)
cov = sum((c - mc) * (e - me) for c, e in zip(got[1:], expected[1:]))
sc = math.sqrt(sum((c - mc) ** 2 for c in got[1:]))
se = math.sqrt(sum((e - me) ** 2 for e in expected[1:]))
corr = cov / (sc * se) if sc and se else 0.0

reset_ok = abs(got[0] - expected[0]) < 0.01
print(f"PASS sample 0 reads loop-start value ({got[0]:+.4f}, expected {expected[0]:+.4f})"
      if reset_ok else
      f"FAIL sample 0 = {got[0]:+.4f}, expected reset value {expected[0]:+.4f}")
print(f"PASS mean abs error {mean_err*100:.3f}% of full-scale (samples 1..{n-1})" if mean_err < 0.01
      else f"FAIL mean abs error {mean_err*100:.3f}% of full-scale (want < 1%)")
print(f"PASS monotonic decreasing {decreasing}/{n-2} steps (samples 1..{n-1})" if decreasing == n - 2
      else f"FAIL monotonic decreasing only {decreasing}/{n-2} steps")
print(f"PASS correlation {corr:.6f} against reversed ramp (samples 1..{n-1})" if corr > 0.999
      else f"FAIL correlation only {corr:.6f} (want > 0.999)")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("reverse audio content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
