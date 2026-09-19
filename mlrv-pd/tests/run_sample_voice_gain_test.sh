#!/usr/bin/env bash
# Verifies sample_voice~.pd's new "gain <value>" message actually scales
# the played-back level, and that leaving it unsent still behaves exactly
# as before (default gain 1.0) -- a real regression guard, not just "loads
# clean". Two independent sample_voice~ instances play the same const
# fixture in parallel: one untouched (default gain), one sent "gain 0.5"
# before its play trigger. Checks the post-fade-in plateau mean of each
# capture against the expected const/1.0 and const/2.0 levels.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-gain-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/gain_test.wav" "$OUT/gain_default.wav" "$OUT/gain_half.wav"

N=2205
PEAK=16000
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/gain_test.wav" "$N" const "$PEAK" || exit 1

# test_sample_voice_gain.pd hardcodes this path -- keep in sync.
cp "$OUT/gain_test.wav" /tmp/mlrv_gain_test.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_sample_voice_gain.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_gain_default.wav "$OUT/gain_default.wav" 2>/dev/null
cp /tmp/mlrv_gain_half.wav "$OUT/gain_half.wav" 2>/dev/null

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/gain_default.wav" "$OUT/gain_half.wav" "$N" "$PEAK" <<'EOF'
import sys, wave, struct

default_path, half_path, n, peak = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])

def read_wav(path, n):
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    if len(vals) != n:
        print(f"FAIL {path} has {len(vals)} samples, expected {n}")
        sys.exit(1)
    return vals

default = read_wav(default_path, n)
half = read_wav(half_path, n)

# skip the 5ms cold-start fade-in (gotcha 12) -- ~240 samples at 48kHz,
# generous margin used here (400) since this test doesn't control the
# real engine sample rate directly.
SKIP = 400
plateau_default = sum(default[SKIP:]) / (n - SKIP)
plateau_half = sum(half[SKIP:]) / (n - SKIP)

want_default = peak
want_half = peak * 0.5

def check(name, got, want, tol_frac=0.02):
    tol = abs(want) * tol_frac + 50
    if abs(got - want) < tol:
        print(f"PASS {name} plateau {got:.1f} (expected ~{want:.1f})")
        return True
    print(f"FAIL {name} plateau {got:.1f}, expected ~{want:.1f} (tol {tol:.1f})")
    return False

ok1 = check("default gain (unset, should behave as before)", plateau_default, want_default)
ok2 = check("gain 0.5", plateau_half, want_half)

# also confirm they're actually different -- rules out a no-op gain message
ratio = plateau_half / plateau_default if plateau_default else 0
if 0.45 < ratio < 0.55:
    print(f"PASS half/default ratio {ratio:.4f} (expected ~0.5)")
else:
    print(f"FAIL half/default ratio {ratio:.4f}, expected ~0.5")
    ok1 = ok2 = False

sys.exit(0 if (ok1 and ok2) else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("gain content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
