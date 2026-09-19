#!/usr/bin/env bash
# Verifies sample_voice~.pd's new "pitch <semitones>" message actually
# changes playback speed by the expected 2^(semitones/12) factor, composed
# with rate (not replacing it) -- not just "loads clean" or "the isolated
# math utility is correct" (both already covered elsewhere), but that the
# wiring between semitones_to_rate and play_loop~'s rate actually works
# end to end against real loaded audio.
#
# Two parallel sample_voice~ instances play the same one-shot linear-ramp
# fixture with rate=1: one untouched (pitch never sent, expected 1x), one
# sent "pitch 12" first (expected 2x = one octave up). At 2x speed, the
# read position sweeps the whole array TWICE within one N-sample capture
# window, wrapping at the midpoint (play_loop~'s phase wraps 1->0, mapped
# position wraps range->0) -- the expected trace is built analytically
# from that, not curve-fit from the actual output.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-pitch-wiring-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/pitch_test.wav" "$OUT/pitch_default.wav" "$OUT/pitch_pitched.wav"

N=2205
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/pitch_test.wav" "$N" || exit 1

# test_sample_voice_pitch.pd hardcodes this path -- keep in sync.
cp "$OUT/pitch_test.wav" /tmp/mlrv_pitch_test.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_sample_voice_pitch.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_pitch_default.wav "$OUT/pitch_default.wav" 2>/dev/null
cp /tmp/mlrv_pitch_pitched.wav "$OUT/pitch_pitched.wav" 2>/dev/null

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/pitch_default.wav" "$OUT/pitch_pitched.wav" "$N" <<'EOF'
import sys, wave, struct, math

default_path, pitched_path, n = sys.argv[1], sys.argv[2], int(sys.argv[3])

def read_wav(path, n):
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    if len(vals) != n:
        print(f"FAIL {path} has {len(vals)} samples, expected {n}")
        sys.exit(1)
    return [v / 32768.0 for v in vals]

def ramp_value(idx):
    # same formula as gen_test_wav.py's ramp mode, idx wrapped into [0, n)
    idx = idx % n
    return (-16000 + 32000 * idx / (n - 1)) / 32768.0

default = read_wav(default_path, n)
pitched = read_wav(pitched_path, n)

SKIP = 400  # 5ms cold-start fade, same margin as the gain test

def corr(got, expected):
    mc = sum(got) / len(got)
    me = sum(expected) / len(expected)
    cov = sum((c - mc) * (e - me) for c, e in zip(got, expected))
    sc = math.sqrt(sum((c - mc) ** 2 for c in got))
    se = math.sqrt(sum((e - me) ** 2 for e in expected))
    return cov / (sc * se) if sc and se else 0.0

expected_default = [ramp_value(i) for i in range(n)]
got_default = default[SKIP:]
c1 = corr(got_default, expected_default[SKIP:])
ok1 = c1 > 0.999
print(f"{'PASS' if ok1 else 'FAIL'} unpitched (rate=1, pitch unset) correlation {c1:.6f} against 1x ramp")

# at 2x speed the array is read fully TWICE within n samples
expected_pitched = [ramp_value(2 * i) for i in range(n)]
got_pitched = pitched[SKIP:]
c2 = corr(got_pitched, expected_pitched[SKIP:])
ok2 = c2 > 0.999
print(f"{'PASS' if ok2 else 'FAIL'} pitch 12 correlation {c2:.6f} against 2x-speed (double-cycle) ramp")

# and NOT well-correlated against the 1x ramp -- rules out a no-op pitch message
c3 = corr(got_pitched, expected_default[SKIP:])
ok3 = c3 < 0.9
print(f"{'PASS' if ok3 else 'FAIL'} pitch 12 vs. 1x-ramp correlation {c3:.6f} (want < 0.9, confirms it's not a no-op)")

sys.exit(0 if (ok1 and ok2 and ok3) else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("pitch content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
