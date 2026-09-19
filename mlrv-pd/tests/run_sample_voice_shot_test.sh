#!/usr/bin/env bash
# Verifies sample_voice~.pd's new "mode shot" message actually plays once
# and auto-stops, vs. "mode loop" (default, unchanged) continuing to
# wrap/repeat -- real captured audio over a window twice the loop length,
# not just a clean load.
#
# Two parallel voices play the same one-shot linear-ramp fixture (N=4410)
# at rate 1: one untouched (loop, default), one sent "mode shot" first.
# Capture window is 2N samples (8820) -- long enough to see both "should
# still be playing/looping" and "should have auto-stopped by now."
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-shot-test"
mkdir -p "$OUT"
rm -f "$OUT"/*.wav "$OUT/pd.log"

N=4410
PEAK=16000
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/shot.wav" "$N" || exit 1

# test_sample_voice_shot.pd hardcodes this path -- keep in sync.
cp "$OUT/shot.wav" /tmp/mlrv_shot_test.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_sample_voice_shot.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_shot_loop.wav "$OUT/loop.wav" 2>/dev/null
cp /tmp/mlrv_shot_shot.wav "$OUT/shot.wav.captured" 2>/dev/null

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/loop.wav" "$OUT/shot.wav.captured" "$N" "$PEAK" <<'EOF'
import sys, wave, struct, math

loop_path, shot_path, n, peak = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
win = 2 * n

def read_wav(path):
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    if len(vals) != win:
        print(f"FAIL {path} has {len(vals)} samples, expected {win}")
        sys.exit(1)
    return [v / 32768.0 for v in vals]

loop = read_wav(loop_path)
shot = read_wav(shot_path)

def ramp_value(idx):
    idx = idx % n
    return (-peak + 2 * peak * idx / (n - 1)) / 32768.0

def corr(got, expected):
    mc = sum(got) / len(got)
    me = sum(expected) / len(expected)
    cov = sum((c - mc) * (e - me) for c, e in zip(got, expected))
    sc = math.sqrt(sum((c - mc) ** 2 for c in got))
    se = math.sqrt(sum((e - me) ** 2 for e in expected))
    return cov / (sc * se) if sc and se else 0.0

SKIP = 400
ok = True

# --- first pass (both should match the plain ramp) ---
expected_pass1 = [ramp_value(i) for i in range(n)]
c_loop1 = corr(loop[SKIP:n], expected_pass1[SKIP:])
c_shot1 = corr(shot[SKIP:n], expected_pass1[SKIP:])
if c_loop1 > 0.999:
    print(f"PASS loop-mode first pass correlation {c_loop1:.6f}")
else:
    print(f"FAIL loop-mode first pass correlation {c_loop1:.6f} (want > 0.999)")
    ok = False
if c_shot1 > 0.999:
    print(f"PASS shot-mode first pass correlation {c_shot1:.6f}")
else:
    print(f"FAIL shot-mode first pass correlation {c_shot1:.6f} (want > 0.999)")
    ok = False

# --- second half: loop-mode should still be making sound (repeats the ramp) ---
expected_pass2 = [ramp_value(i) for i in range(n)]
c_loop2 = corr(loop[n + SKIP:win], expected_pass2[SKIP:])
if c_loop2 > 0.999:
    print(f"PASS loop-mode second pass correlation {c_loop2:.6f} (confirms it wrapped/repeated)")
else:
    print(f"FAIL loop-mode second pass correlation {c_loop2:.6f} (want > 0.999, expected a repeat)")
    ok = False

# --- second half: shot-mode should be silent (auto-stopped) ---
# generous margin past the loop point for the 5ms fade-out + scheduling slop
tail = shot[n + 1000:win]
peak_tail = max(abs(v) for v in tail)
if peak_tail < 0.01:
    print(f"PASS shot-mode silent after auto-stop, tail peak {peak_tail:.5f} (want < 0.01)")
else:
    print(f"FAIL shot-mode NOT silent after expected auto-stop, tail peak {peak_tail:.5f} (want < 0.01)")
    ok = False

# --- confirm the auto-stop actually happens near the expected sample n, not
# way early or way late: find the last sample index whose magnitude is still
# "playing-level" (> 10% of peak) before the tail region
threshold = 0.1
last_loud = None
for i in range(n - 500, n + 500):
    if abs(shot[i]) > threshold:
        last_loud = i
if last_loud is not None and (n - 500) <= last_loud <= (n + 500):
    print(f"PASS shot-mode auto-stop lands near sample {n} (last loud sample: {last_loud})")
else:
    print(f"FAIL shot-mode auto-stop timing off -- last loud sample: {last_loud}, expected near {n}")
    ok = False

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("shot mode content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
