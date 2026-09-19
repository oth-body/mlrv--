#!/usr/bin/env bash
# Verifies file_poly.pd's new top-level `gain <voice> <value>` and
# `pitch <voice> <semitones>` messages actually reach the right
# sample_voice~ instance through the real public interface -- not just
# that sample_voice~.pd's own gain/pitch messages work in isolation
# (covered by run_sample_voice_gain_test.sh / run_sample_voice_pitch_test.sh),
# but that file_poly.pd's dispatch wiring built this turn actually routes
# them to the correct one of 4 voices.
#
# Four isolated single-voice captures (see build_test_file_poly_gain_pitch.py):
# voice 1 (const, default gain), voice 2 (const, gain 0.5), voice 3 (ramp,
# default pitch), voice 4 (ramp, pitch 12).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fpgp-test"
mkdir -p "$OUT"
rm -f "$OUT"/*.wav "$OUT/pd.log"

N=2205
PEAK=16000
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/const.wav" "$N" const "$PEAK" || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/ramp.wav" "$N" || exit 1

# test_file_poly_gain_pitch.pd hardcodes these paths -- keep in sync.
cp "$OUT/const.wav" /tmp/mlrv_fpgp_const.wav
cp "$OUT/ramp.wav" /tmp/mlrv_fpgp_ramp.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions:mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly_gain_pitch.pd > "$OUT/pd.log" 2>&1

for f in gain_default gain_half pitch_default pitch_shifted; do
    cp "/tmp/mlrv_fpgp_${f}.wav" "$OUT/${f}.wav" 2>/dev/null
done

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT" "$N" "$PEAK" <<'EOF'
import sys, wave, struct, math

out, n, peak = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

def read_wav(name):
    path = f"{out}/{name}.wav"
    try:
        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        print(f"FAIL {path} was not written")
        sys.exit(1)
    if len(vals) != n:
        print(f"FAIL {path} has {len(vals)} samples, expected {n}")
        sys.exit(1)
    return [v / 32768.0 for v in vals]

SKIP = 400
gd = read_wav("gain_default")
gh = read_wav("gain_half")
pdft = read_wav("pitch_default")
ps = read_wav("pitch_shifted")

ok = True

# --- gain dispatch ---
plateau_gd = sum(gd[SKIP:]) / (n - SKIP)
plateau_gh = sum(gh[SKIP:]) / (n - SKIP)
want_gd = peak / 32768.0
want_gh = 0.5 * peak / 32768.0

def check(name, got, want, tol_frac=0.02):
    tol = abs(want) * tol_frac + 0.002
    if abs(got - want) < tol:
        print(f"PASS {name} = {got:.4f} (expected ~{want:.4f})")
        return True
    print(f"FAIL {name} = {got:.4f}, expected ~{want:.4f} (tol {tol:.4f})")
    return False

ok &= check("voice1 default gain plateau", plateau_gd, want_gd)
ok &= check("voice2 gain-0.5-via-file_poly plateau", plateau_gh, want_gh)

ratio = plateau_gh / plateau_gd if plateau_gd else 0
if 0.45 < ratio < 0.55:
    print(f"PASS gain half/default ratio {ratio:.4f} (expected ~0.5)")
else:
    print(f"FAIL gain half/default ratio {ratio:.4f}, expected ~0.5")
    ok = False

# --- pitch dispatch ---
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

expected_1x = [ramp_value(i) for i in range(n)]
expected_2x = [ramp_value(2 * i) for i in range(n)]

c1 = corr(pdft[SKIP:], expected_1x[SKIP:])
c2 = corr(ps[SKIP:], expected_2x[SKIP:])
c3 = corr(ps[SKIP:], expected_1x[SKIP:])

if c1 > 0.999:
    print(f"PASS voice3 default pitch correlation {c1:.6f} against 1x ramp")
else:
    print(f"FAIL voice3 default pitch correlation {c1:.6f} (want > 0.999)")
    ok = False

if c2 > 0.999:
    print(f"PASS voice4 pitch-12-via-file_poly correlation {c2:.6f} against 2x-speed ramp")
else:
    print(f"FAIL voice4 pitch-12-via-file_poly correlation {c2:.6f} (want > 0.999)")
    ok = False

if c3 < 0.9:
    print(f"PASS voice4 vs 1x-ramp correlation {c3:.6f} (want < 0.9, confirms not a no-op)")
else:
    print(f"FAIL voice4 vs 1x-ramp correlation {c3:.6f} (want < 0.9)")
    ok = False

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("gain/pitch dispatch content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
