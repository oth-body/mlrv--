#!/usr/bin/env bash
# Verifies master.pd end to end against exact expected signals:
#   - gain scaling (1.0 / 0.5 / 4.0)
#   - tanh soft-clip limiting (gain 4.0 saturates, never exceeds ~0.98)
#   - fx buses: send~ fxout taps the PRE-clip dry ramp exactly;
#     receive~ fxin (0.1 DC) sums into the mix pre-clip
#   - meter: env~-dB outlet peaks at the gain-4 window (~99.8 dB,
#     100+20*log10(tanh(4.8*0.4883))) and holds ~94.4 dB on the const
#     window (100+20*log10(tanh(1.2*16000/32768)))
# Timeline lives in test_master.pd's header comment.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-master-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT"/*.wav /tmp/mlrv_mstr_*.wav /tmp/mlrv_mstr_cap_*.wav

RAMP=4410
CONST=1024

python3 mlrv-pd/tests/gen_test_wav.py "$OUT/ramp.wav"  "$RAMP"  ramp 16000  || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/const.wav" "$CONST" const 16000 || exit 1

# test_master.pd hardcodes these paths -- keep in sync.
cp "$OUT/ramp.wav"  /tmp/mlrv_mstr_ramp.wav
cp "$OUT/const.wav" /tmp/mlrv_mstr_const.wav

timeout 6 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_master.pd > "$OUT/pd.log" 2>&1
for c in a b c d e f; do cp /tmp/mlrv_mstr_cap_$c.wav "$OUT/cap_$c.wav" 2>/dev/null; done

PASS=()
FAIL=()

check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

for c in a b c d e f; do
    if [ -s "$OUT/cap_$c.wav" ]; then PASS+=("capture cap_$c written"); else FAIL+=("capture cap_$c written"); fi
done

# --- python analysis: exact expected signals for all six captures + meter ---
PYOUT="$(python3 - "$OUT/pd.log" "$OUT" "$RAMP" <<'EOF'
import math, re, struct, sys, wave

log, outdir, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
ok = lambda cond, msg: (f"PASS {msg}" if cond else f"FAIL {msg}", cond)
rows = []


def read_wav(name):
    try:
        with wave.open(f"{outdir}/{name}", "rb") as w:
            data = w.readframes(w.getnframes())
            return struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        return None


def ramp_ints(n):
    return [round(-16000 + 32000 * i / (n - 1)) for i in range(n)]


def stats(got, exp):
    n = len(exp)
    g, e = got[:n], exp
    mg, me = sum(g) / n, sum(e) / n
    cov = sum((c - mg) * (x - me) for c, x in zip(g, e))
    sg = math.sqrt(sum((c - mg) ** 2 for c in g))
    se = math.sqrt(sum((x - me) ** 2 for x in e))
    corr = cov / (sg * se) if sg and se else 0.0
    mean_err = sum(abs(c - x) for c, x in zip(g, e)) / n
    frac = mean_err / (max(e) - min(e)) * 100.0
    return corr, frac


def check_capture(name, exp, ok_corr=0.999, ok_frac=1.0):
    got = read_wav(name)
    if got is None:
        rows.append(ok(False, f"{name}: wav written"))
        return None
    corr, frac = stats(got, exp)
    good = corr > ok_corr and frac < ok_frac
    rows.append((ok(good, f"{name} match: corr {corr:.6f}, mean err {frac:.3f}%"), good))
    return got


rv = ramp_ints(n)

# A: dry ramp, gain 1 -> tanh(1.2*x)
exp_a = [round(math.tanh(1.2 * v / 32768.0) * 32768) for v in rv]
got_a = check_capture("cap_a.wav", exp_a, 0.999, 1.0)

# B: ramp + 0.1 fx return, gain 1 -> tanh(1.2*(x+0.1))
exp_b = [round(math.tanh(1.2 * (v / 32768.0 + 0.1)) * 32768) for v in rv]
check_capture("cap_b.wav", exp_b, 0.999, 1.0)

# C: fxout send = PRE-clip dry ramp, but send~/receive~ across the
# abstraction boundary lag by exactly one DSP block (64 samples @ default
# block size): the first block receive~ hears is stale (last block before
# the retrigger), then the ramp from position 0. Measure the shift rather
# than assume it.
got_c = read_wav("cap_c.wav")
if got_c is None:
    rows.append(ok(False, "cap_c.wav: wav written"))
else:
    best_s, best_e = 0, 1e18
    for s in range(0, 200):
        seg = range(max(s, 64), 4410)
        e = sum(abs(got_c[i] - rv[i - s]) for i in seg) / len(seg)
        if e < best_e:
            best_e, best_s = e, s
    good = best_s == 64 and best_e < 2.0
    rows.append((ok(good, f"cap_c fxout pre-clip, lag {best_s} samples == one DSP block, "
                          f"mean err {best_e:.3f}"), good))

# D: ramp, gain 0.5 -> tanh(0.6*x)
exp_d = [round(math.tanh(0.6 * v / 32768.0) * 32768) for v in rv]
got_d = check_capture("cap_d.wav", exp_d, 0.999, 1.0)

# E: ramp, gain 4 -> tanh(4.8*x): soft-clip limiting
exp_e = [round(math.tanh(4.8 * v / 32768.0) * 32768) for v in rv]
got_e = check_capture("cap_e.wav", exp_e, 0.999, 1.0)
if got_e is not None:
    pk = max(abs(x) for x in got_e)
    good = pk <= round(0.99 * 32768) and pk >= 31800
    rows.append((ok(good, f"cap_e soft-limit holds: peak {pk} (linear would be ~64000)"), good))

# F: const DC -> flat tanh(1.2*16000/32768)
exp_f = round(math.tanh(1.2 * 16000 / 32768.0) * 32768)
got_f = read_wav("cap_f.wav")
if got_f is None:
    rows.append(ok(False, "cap_f: wav written"))
else:
    mn, mx = min(got_f), max(got_f)
    mean = sum(got_f) / len(got_f)
    good = abs(mean - exp_f) <= 4 and mx - mn <= 3
    rows.append((ok(good, f"cap_f flat {exp_f}: mean {mean:.1f} spread {mx-mn}"), good))

# gain scaling + pre-clip sanity: cap_d peak < cap_a peak; fxout peak < out peak
if got_a is not None and got_d is not None:
    pa = max(abs(x) for x in got_a)
    pd = max(abs(x) for x in got_d)
    rows.append((ok(pd < pa, f"gain scales: cap_d peak {pd} < cap_a peak {pa}"), pd < pa))
if got_c is not None and got_a is not None:
    pc = max(abs(x) for x in got_c)
    pa = max(abs(x) for x in got_a)
    rows.append((ok(pc < pa, f"fxout pre-clip: fxout peak {pc} < clipped out peak {pa}"), pc < pa))

# --- meter (env~): dB with full scale = 100 ---
meters = []
for line in open(log, errors="replace"):
    m = re.match(r"^mstr_meter: (\S+)", line)
    if m:
        try:
            meters.append(float(m.group(1)))
        except ValueError:
            pass
rows.append((ok(len(meters) > 100, f"meter emits ({len(meters)} prints)"), len(meters) > 100))
if meters:
    mx = max(meters)
    good = 99.3 <= mx <= 100.3
    rows.append((ok(good, f"meter max on gain-4 window {mx:.2f} dB (expect ~99.84)"), good))
    last = meters[-30:]
    lm = sum(last) / len(last)
    good = 93.5 <= lm <= 95.5
    rows.append((ok(good, f"meter const-window steady {lm:.2f} dB (expect ~94.43)"), good))

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