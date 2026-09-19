#!/usr/bin/env bash
# Verifies file_poly.pd's new top-level `mode <voice> <loop|shot>` message
# actually reaches the right sample_voice~ instance through the real
# public interface -- not just that sample_voice~.pd's own "mode" message
# works in isolation (covered by run_sample_voice_shot_test.sh), but that
# file_poly.pd's dispatch wiring built this turn actually routes it.
#
# Two isolated single-voice captures over a 2N window (see
# build_test_file_poly_mode.py): voice 1 (default mode = loop, should
# keep making sound through the whole window), voice 2 (mode 2 shot sent
# first, should auto-stop partway through).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fpmode-test"
mkdir -p "$OUT"
rm -f "$OUT"/*.wav "$OUT/pd.log"

N=4410
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/ramp.wav" "$N" || exit 1

# test_file_poly_mode.pd hardcodes this path -- keep in sync.
cp "$OUT/ramp.wav" /tmp/mlrv_fpmode_ramp.wav

timeout 6 pd -nogui -stderr -path mlrv-pd/abstractions:mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly_mode.pd > "$OUT/pd.log" 2>&1

cp /tmp/mlrv_fpmode_loop.wav "$OUT/loop.wav" 2>/dev/null
cp /tmp/mlrv_fpmode_shot.wav "$OUT/shot.wav" 2>/dev/null

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

PYOUT="$(python3 - "$OUT/loop.wav" "$OUT/shot.wav" "$N" <<'EOF'
import sys, wave, struct, math

loop_path, shot_path, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
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
    return (-16000 + 32000 * idx / (n - 1)) / 32768.0

def corr(got, expected):
    mc = sum(got) / len(got)
    me = sum(expected) / len(expected)
    cov = sum((c - mc) * (e - me) for c, e in zip(got, expected))
    sc = math.sqrt(sum((c - mc) ** 2 for c in got))
    se = math.sqrt(sum((e - me) ** 2 for e in expected))
    return cov / (sc * se) if sc and se else 0.0

SKIP = 400
ok = True

expected1 = [ramp_value(i) for i in range(n)]
c_loop1 = corr(loop[SKIP:n], expected1[SKIP:])
c_shot1 = corr(shot[SKIP:n], expected1[SKIP:])
if c_loop1 > 0.999:
    print(f"PASS voice1 (default/loop) first pass correlation {c_loop1:.6f}")
else:
    print(f"FAIL voice1 (default/loop) first pass correlation {c_loop1:.6f}")
    ok = False
if c_shot1 > 0.999:
    print(f"PASS voice2 (mode 2 shot) first pass correlation {c_shot1:.6f}")
else:
    print(f"FAIL voice2 (mode 2 shot) first pass correlation {c_shot1:.6f}")
    ok = False

c_loop2 = corr(loop[n + SKIP:win], expected1[SKIP:])
if c_loop2 > 0.999:
    print(f"PASS voice1 second pass correlation {c_loop2:.6f} (confirms loop repeats)")
else:
    print(f"FAIL voice1 second pass correlation {c_loop2:.6f} (expected a repeat)")
    ok = False

tail = shot[n + 1000:win]
peak_tail = max(abs(v) for v in tail)
if peak_tail < 0.01:
    print(f"PASS voice2 silent after auto-stop via file_poly dispatch, tail peak {peak_tail:.5f}")
else:
    print(f"FAIL voice2 NOT silent after expected auto-stop, tail peak {peak_tail:.5f}")
    ok = False

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("mode dispatch content check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
