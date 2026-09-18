#!/usr/bin/env bash
# Verifies mapping.pd end to end: grid presses -> control messages into the
# real file_poly.pd, real loaded audio out, and the LED chain
# (mapping -> grid.pd -> print). Timeline lives in test_mapping.pd; see its
# header comment for the exact events and expected messages.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-map-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/mp_long.wav" "$OUT/mp_short.wav" "$OUT/cap.wav"

N_LONG=4410
N_SHORT=2205

python3 mlrv-pd/tests/gen_test_wav.py "$OUT/mp_long.wav"  "$N_LONG"  ramp  || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/mp_short.wav" "$N_SHORT" const 12000 || exit 1

# test_mapping.pd hardcodes these paths -- keep in sync.
cp "$OUT/mp_long.wav"  /tmp/mlrv_mp_long.wav
cp "$OUT/mp_short.wav" /tmp/mlrv_mp_short.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mapping.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_mp_cap.wav "$OUT/cap.wav" 2>/dev/null

PASS=()
FAIL=()

check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

# --- loaded reports (info outlet feeds mapping + FINFO tap) ---
if grep -q '^finfo: loaded 0 4410' "$OUT/pd.log"; then PASS+=("load report: loaded 0 4410"); else FAIL+=("load report: loaded 0 4410"); fi
if grep -q '^finfo: loaded 1 2205' "$OUT/pd.log"; then PASS+=("load report: loaded 1 2205"); else FAIL+=("load report: loaded 1 2205"); fi

# --- control-message sequence exactly: play0, play1, stopall, play0 ---
CTRL="$(grep -o '^mctrl: .*' "$OUT/pd.log" | sed 's/^mctrl: //' | tr '\n' '|')"
EXPECT_CTRL="play 0 1 0 4410|play 1 1 0 2205|stopall|play 0 1 0 4410|"
if [ "$CTRL" = "$EXPECT_CTRL" ]; then
    PASS+=("control sequence exactly: play0, play1, stopall, play0")
else
    FAIL+=("control sequence: got '$CTRL'")
fi

# --- voice allocation: 1 2 3 ---
VOICES="$(grep -o '^finfo: voice [0-9]*' "$OUT/pd.log" | awk '{print $3}' | tr '\n' ' ' | sed 's/ $//')"
if [ "$VOICES" = "1 2 3" ]; then PASS+=("voice allocation: exactly 1 2 3"); else FAIL+=("voice allocation: got '$VOICES'"); fi

# --- guarded slots: unloaded trigger / release / off-row presses emit nothing ---
if grep -q '^mctrl: play 4' "$OUT/pd.log"; then FAIL+=("unloaded slot 4 never plays"); else PASS+=("unloaded slot 4 never plays"); fi
if grep -q '^mled: 4 7 15' "$OUT/pd.log"; then FAIL+=("unloaded slot 4 never lights"); else PASS+=("unloaded slot 4 never lights"); fi
if grep -q '^mctrl: play 0 1 0 0' "$OUT/pd.log"; then FAIL+=("no zero-length play (guard)"); else PASS+=("no zero-length play (guard)"); fi
if grep -q '^mctrl: play [237] ' "$OUT/pd.log"; then FAIL+=("only slots 0 and 1 ever play"); else PASS+=("only slots 0 and 1 ever play"); fi

# --- LED trigger lights + stopall clears ---
for LED in "0 7 15" "1 7 15"; do
    if grep -q "^mled: $LED\$" "$OUT/pd.log"; then PASS+=("lead LED $LED"); else FAIL+=("lead LED $LED"); fi
done
CLEARS_OK=1
for i in 0 1 2 3 4 5 6 7; do
    grep -q "^mled: $i 7 0\$" "$OUT/pd.log" || CLEARS_OK=0
done
if [ "$CLEARS_OK" = "1" ]; then PASS+=("stopall clears all 8 trigger LEDs"); else FAIL+=("stopall clears all 8 trigger LEDs"); fi

# --- python analysis: capture audio = ramp alone (post-stopall cold start) ---
PYOUT="$(python3 - "$OUT/pd.log" "$OUT/cap.wav" "$N_LONG" <<'EOF'
import math, re, struct, sys, wave

log, cap, n_long = sys.argv[1], sys.argv[2], int(sys.argv[3])
ok = lambda cond, msg: (f"PASS {msg}" if cond else f"FAIL {msg}", cond)
rows = []


def read_wav(path):
    try:
        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            return struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        return None


def seam_cells(period):
    """play_loop~ tabread4~ seam cells (documented): margin of 4 either side
    of the period-4410 wrap in the 4410-sample window."""
    return [k % period < 4 or k % period >= period - 4 for k in range(4410)]


SEAM = seam_cells(n_long)
FADE = [k < 256 for k in range(4410)]   # 5ms cold-start fade-in + margin
MASK = [s or f for s, f in zip(SEAM, FADE)]

long_i = [round(-16000 + 32000 * i / (n_long - 1)) for i in range(n_long)]
got = read_wav(cap)
if got is None:
    rows.append(ok(False, "capture wav was written"))
else:
    idx = [i for i in range(len(got)) if not MASK[i]]
    n = len(idx)
    g = [got[i] for i in idx]
    e = [long_i[i] for i in idx]
    mean_err = sum(abs(c - x) for c, x in zip(g, e)) / n
    mg, me = sum(g) / n, sum(e) / n
    cov = sum((c - mg) * (x - me) for c, x in zip(g, e))
    sg = math.sqrt(sum((c - mg) ** 2 for c in g))
    se = math.sqrt(sum((x - me) ** 2 for x in e))
    corr = cov / (sg * se) if sg and se else 0.0
    frac = mean_err / (max(e) - min(e)) * 100.0
    ok1 = corr > 0.999
    ok2 = frac < 1.0
    rows.append((ok(ok1 and ok2, f"grid->audio capture = long ramp: corr {corr:.6f}, "
                              f"mean abs err {frac:.3f}% (clean {n}/4410)")[0], ok1 and ok2))

for r, _ in rows:
    print(r)
print("FAIL" if any(not ok for _, ok in rows) else "PASS")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q '^FAIL'; then FAIL+=("audio analysis"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]