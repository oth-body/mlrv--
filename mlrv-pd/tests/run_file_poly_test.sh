#!/usr/bin/env bash
# Verifies file_poly.pd end to end: sample loading, round-robin voice
# allocation, polyphonic playback, and voice stopping -- against real
# loaded audio content, not a clean-load-only check.
#
# Timeline exercised (all inside test_file_poly.pd):
#   load 0 <ramp 4410>   -> fp: loaded 0 4410
#   load 3 <const 2205>  -> fp: loaded 3 2205
#   content/size probes  -> probeA/B (tabread at index 0), probeC/D (array size)
#   5x play              -> fp: voice 1 2 3 4 1 (round-robin, exactly 5)
#   stopall
#   playv 1 3 ... + playv 2 0 ...  -> overlapping polyphony, captured
#   stop 1               -> constant voice fades out, ramp voice keeps going
#
# Capture analysis excludes two documented artifacts:
#   - the play_loop~ tabread4~ seam cells (periodic, both captures)
#   - the 5ms sample_voice~ fade-in written into capture1's first ~220
#     cells (both voices are cold-started in the arm tick; capture2's
#     voice2 re-trigger finds line~ already at 1, so it has no fade)
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fp-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/fp_long.wav" "$OUT/fp_short.wav" \
      "$OUT/cap1.wav" "$OUT/cap2.wav"

N_LONG=4410
N_SHORT=2205
CONST_PEAK=12000

python3 mlrv-pd/tests/gen_test_wav.py "$OUT/fp_long.wav"  "$N_LONG"  ramp  || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/fp_short.wav" "$N_SHORT" const "$CONST_PEAK" || exit 1

# test_file_poly.pd hardcodes these paths -- keep in sync.
cp "$OUT/fp_long.wav"  /tmp/mlrv_fp_long.wav
cp "$OUT/fp_short.wav" /tmp/mlrv_fp_short.wav

timeout 5 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly.pd > "$OUT/pd.log" 2>&1
cp /tmp/mlrv_fp_cap1.wav "$OUT/cap1.wav" 2>/dev/null
cp /tmp/mlrv_fp_cap2.wav "$OUT/cap2.wav" 2>/dev/null

PASS=()
FAIL=()

check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

# --- info-line checks (loaded reports, no premature-fire regression) ---
if grep -q '^fp: loaded 0 4410' "$OUT/pd.log"; then PASS+=("load report: loaded 0 4410"); else FAIL+=("load report: loaded 0 4410"); fi
if grep -q '^fp: loaded 3 2205' "$OUT/pd.log"; then PASS+=("load report: loaded 3 2205"); else FAIL+=("load report: loaded 3 2205"); fi
if grep -q '^fp: loaded 0 0' "$OUT/pd.log"; then
    FAIL+=("no premature loaded 0 0 (slot-holder left-inlet regression)")
else
    PASS+=("no premature loaded 0 0 (slot-holder left-inlet regression)")
fi

# --- voice-allocation sequence: 5x play + 2x playv + 1x playv retrigger ---
#    = 1 2 3 4 1, 1 2, then 2. Every line is asserted, wrong count fails.
VOICES="$(grep -o '^fp: voice [0-9]*' "$OUT/pd.log" | awk '{print $3}' | tr '\n' ' ' | sed 's/ $//')"
if [ "$VOICES" = "1 2 3 4 1 1 2 2" ]; then PASS+=("voice allocation: exactly 1 2 3 4 1 1 2 2"); else FAIL+=("voice allocation: got '$VOICES'"); fi

# --- python analysis of probes + captured audio ---
PYOUT="$(python3 - "$OUT/pd.log" "$OUT/cap1.wav" "$OUT/cap2.wav" "$N_LONG" "$N_SHORT" "$CONST_PEAK" <<'EOF'
import math, re, struct, sys, wave

log, cap1, cap2, n_long, n_short, const_peak = (
    sys.argv[1], sys.argv[2], sys.argv[3],
    int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]))

# --- probe values from the pd log ---
probes = {}
for name in ("probeA", "probeB", "probeC", "probeD"):
    m = re.search(rf"^{name}: (\S+)", open(log).read(), re.M)
    probes[name] = float(m.group(1)) if m else None

ok = lambda cond, msg: (f"PASS {msg}" if cond else f"FAIL {msg}", cond)

rows = []
exp_a = -16000 / 32768.0
exp_b = const_peak / 32768.0
rows.append(ok(probes["probeA"] is not None and abs(probes["probeA"] - exp_a) < 0.003,
               f"probeA tabread mlrv-sample-0[0] ~ {exp_a:.4f} (got {probes['probeA']})"))
rows.append(ok(probes["probeB"] is not None and abs(probes["probeB"] - exp_b) < 0.003,
               f"probeB tabread mlrv-sample-3[0] ~ {exp_b:.4f} (got {probes['probeB']})"))
rows.append(ok(probes["probeC"] == n_long,
               f"probeC array size mlrv-sample-0 == {n_long} (got {probes['probeC']})"))
rows.append(ok(probes["probeD"] == n_short,
               f"probeD array size mlrv-sample-3 == {n_short} (got {probes['probeD']})"))


def read_wav(path):
    try:
        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            return struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        return None


def seam_cells(period):
    """Cells corrupted by play_loop~'s documented tabread4~ seam artifact:
    the 4-point interpolation window reads up to ~2 samples past loop bounds.
    Exclude a 4-sample margin either side of the seam (period -> 0 wrap).
    For capture1 the const voice exerts its seam at period=2205 and the ramp
    voice at period=4410; capture2 only the ramp's. The mask is periodic
    over the 4410-sample capture window."""
    mask = [False] * 4410
    for k in range(4410):
        r = k % period
        if r >= period - 4 or r <= 3:
            mask[k] = True
    return mask


SEAM1 = [a or b for a, b in zip(seam_cells(2205), seam_cells(4410))]
SEAM2 = seam_cells(4410)
FADE = [k < 256 for k in range(4410)]  # 5ms voice fade-in (220 cells) + margin
MASK1 = [s or f for s, f in zip(SEAM1, FADE)]


def compare(name, got, expected, seammask):
    """got/expected: lists of int16 over length-4410 windows. Cells in
    seammask (the known seam-corrupted positions) are excluded from both
    correlation and mean error."""
    if got is None:
        return f"FAIL {name}: capture wav was not written", False
    if len(got) != len(expected):
        return f"FAIL {name}: {len(got)} samples, expected {len(expected)}", False
    idx = [i for i in range(len(got)) if not seammask[i]]
    n = len(idx)
    g = [got[i] for i in idx]
    e = [expected[i] for i in idx]
    mean_err = sum(abs(c - x) for c, x in zip(g, e)) / n
    mg = sum(g) / n
    me = sum(e) / n
    cov = sum((c - mg) * (x - me) for c, x in zip(g, e))
    sg = math.sqrt(sum((c - mg) ** 2 for c in g))
    se = math.sqrt(sum((x - me) ** 2 for x in e))
    corr = cov / (sg * se) if sg and se else 0.0
    scale = (max(e) - min(e)) or 1.0
    frac = mean_err / scale * 100.0
    ok1 = corr > 0.999
    ok2 = frac < 1.0
    report = (f"{'PASS' if ok1 and ok2 else 'FAIL'} {name}: corr {corr:.6f}, "
              f"mean abs err {frac:.3f}% of signal range "
              f"(clean cells {n}/{len(got)})")
    return report, ok1 and ok2


long_i = [round(-16000 + 32000 * i / (n_long - 1)) for i in range(n_long)]
cap1_got = read_wav(cap1)
cap2_got = read_wav(cap2)
exp1 = [long_i[i] + const_peak for i in range(n_long)]           # ramp + const
exp2 = [long_i[i] for i in range(n_long)]                        # ramp alone (re-triggered at capture-2 arm)

# capture1: both voices together = ramp + const (exact, wrap trick, phase 0);
# its 5ms fade-in cells are documented in MASK1 (seam + fade)
r1, ok1 = compare("polyphony capture1 (const voice1 + ramp voice2)", cap1_got, exp1, MASK1)
rows.append((r1, ok1))
# capture2: after stop 1, voice2 re-triggered at arm time = ramp alone:
# corr high proves the surviving voice plays; mean err tiny proves the
# stopped const voice contributes ~zero (no leftover +12000 offset)
r2, ok2 = compare("post-stop capture2 (ramp voice2 alone)", cap2_got, exp2, SEAM2)
rows.append((r2, ok2))

for r, _ in rows:
    print(r)
print("FAIL" if any(not ok for _, ok in rows) else "PASS")
EOF
)"
echo "$PYOUT"
if echo "$PYOUT" | grep -q '^FAIL'; then FAIL+=("python analysis"); fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]