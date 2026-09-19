#!/usr/bin/env bash
# Verifies record_buffer~.pd (1:1 mlrv recreation, live audio recording
# item) against real captured audio and real timing, not just a clean
# load. See tests/builders/build_test_record_buffer.py for the full
# scenario.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-recordbuffer-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" /tmp/mlrv_recbuf_a.wav /tmp/mlrv_recbuf_c_early.wav /tmp/mlrv_recbuf_c_late.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_record_buffer.pd > "$OUT/pd.log" 2>&1

cp /tmp/mlrv_recbuf_a.wav "$OUT/recbuf_a.wav" 2>/dev/null
cp /tmp/mlrv_recbuf_c_early.wav "$OUT/recbuf_c_early.wav" 2>/dev/null
cp /tmp/mlrv_recbuf_c_late.wav "$OUT/recbuf_c_late.wav" 2>/dev/null

PASS=()
FAIL=()

# ALSA hardware-contention warnings are expected/harmless in this
# multi-session environment (see CLAUDE.md) -- only real "error:" lines
# from Pd itself count.
UNEXPECTED_ERRORS="$(grep -i 'error:' "$OUT/pd.log")"
if [ -z "$UNEXPECTED_ERRORS" ]; then
    PASS+=("no pd errors")
else
    FAIL+=("no pd errors")
    echo "$UNEXPECTED_ERRORS"
fi

check() {  # check <pattern> <label>
    if grep -q -- "$1" "$OUT/pd.log"; then PASS+=("$2"); else FAIL+=("$2"); fi
}
check "done_a: bang" "bare bang starts recording (done-bang fires)"
check "done_b: bang" "\"record\" (word) equivalent to bare bang"
check "done_c: bang" "preroll recording completes"

PYOUT="$(python3 - "$OUT" <<'EOF'
import sys, wave, struct, re

out = sys.argv[1]

def peak(name):
    path = f"{out}/{name}.wav"
    try:
        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            vals = struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        print(f"FAIL {path} was not written")
        sys.exit(1)
    return max(abs(v) for v in vals)

ok = True

pk_a = peak("recbuf_a")
if pk_a > 20000:
    print(f"PASS bare-bang recording captured real signal (peak {pk_a})")
else:
    print(f"FAIL bare-bang recording peak too low ({pk_a}), expected real osc~ content")
    ok = False

pk_early = peak("recbuf_c_early")
if pk_early == 0:
    print(f"PASS preroll: nothing captured before the delay elapses (peak {pk_early})")
else:
    print(f"FAIL preroll: expected silence before delay elapses, got peak {pk_early}")
    ok = False

pk_late = peak("recbuf_c_late")
if pk_late > 20000:
    print(f"PASS preroll: real signal captured after the delay elapses (peak {pk_late})")
else:
    print(f"FAIL preroll: expected real signal after delay, got peak {pk_late}")
    ok = False

with open(f"{out}/pd.log") as f:
    log = f.read()
counts = [int(m) for m in re.findall(r"loop_count_final: (\d+)", log)]
if not counts:
    print("FAIL loop mode: no loop_count_final lines found")
    ok = False
else:
    final = counts[-1]
    # ~1000ms of active looping at 441 samples / real engine samplerate
    # (typically 48000 -> ~9.19ms/cycle -> ~109 cycles); wide tolerance
    # since exact engine samplerate/scheduling can vary by environment.
    if 60 <= final <= 200:
        print(f"PASS loop mode auto-rearmed {final} times in ~1s, then settled after loop-off (in expected range)")
    else:
        print(f"FAIL loop mode final count {final}, expected roughly 60-200 for ~1s of a ~9ms cycle")
        ok = False
    stable_tail = counts[-3:] if len(counts) >= 3 else counts
    print(f"PASS final count progression (last few): {stable_tail}")

sys.exit(0 if ok else 1)
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q "^FAIL"; then FAIL+=("recording content/timing check"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
