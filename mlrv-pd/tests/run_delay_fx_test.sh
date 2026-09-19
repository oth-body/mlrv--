#!/usr/bin/env bash
# Verifies delay_fx~.pd against real captured audio (not just a clean
# load): a short burst through `time 200, feedback 0` should produce
# exactly one delayed copy and silence everywhere else; through
# `time 200, feedback 0.5` (fired 600ms later, well after the first
# scenario's single echo has decayed) it should produce three copies
# 200ms apart, each roughly half the peak of the last (geometric decay).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-delay-fx-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" /tmp/mlrv_dfx_burst.wav /tmp/mlrv_dfx_cap1.wav /tmp/mlrv_dfx_cap2.wav

python3 mlrv-pd/tests/gen_test_wav.py /tmp/mlrv_dfx_burst.wav 100 const 16000 || exit 1

timeout 6 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_delay_fx.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi

python3 - "$OUT" <<'PYEOF'
import sys, wave, struct

out = sys.argv[1]

def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        sr = w.getframerate()
        samples = struct.unpack(f"<{n}h", w.readframes(n))
        return samples, sr

def find_peaks(samples, thresh=1000):
    peaks = []
    i, n = 0, len(samples)
    while i < n:
        if abs(samples[i]) >= thresh:
            j, peakval = i, 0
            while j < n and abs(samples[j]) >= thresh:
                peakval = max(peakval, abs(samples[j]))
                j += 1
            peaks.append((i, j, peakval))
            i = j
        else:
            i += 1
    return peaks

results = []

s1, sr1 = load("/tmp/mlrv_dfx_cap1.wav")
p1 = find_peaks(s1)
results.append(("cap1: exactly one region (feedback=0 produces no echo)", len(p1) == 1))
if p1:
    t_ms = p1[0][0] / sr1 * 1000
    # requested 200ms + 2 send~/receive~ block hops (gotcha 16, crossed twice
    # here: test->delay_fx~ and delay_fx~->test) -- expect ~202.7ms at 48kHz/64
    results.append((f"cap1: region timing ~202.7ms (got {t_ms:.2f}ms)", 201 <= t_ms <= 205))
    results.append((f"cap1: region peak near 16000 (got {p1[0][2]})", 15500 <= p1[0][2] <= 16000))

s2, sr2 = load("/tmp/mlrv_dfx_cap2.wav")
p2 = find_peaks(s2)
results.append((f"cap2: exactly three regions (direct echo + 2 feedback repeats, got {len(p2)})", len(p2) == 3))
if len(p2) == 3:
    gaps = [(p2[i+1][0] - p2[i][0]) / sr2 * 1000 for i in range(2)]
    results.append((f"cap2: repeats spaced ~200ms apart (got {gaps})", all(198 <= g <= 202 for g in gaps)))
    peaks = [p[2] for p in p2]
    ratios = [peaks[i+1] / peaks[i] for i in range(2)]
    results.append((f"cap2: each repeat ~half the last (feedback=0.5, ratios {[round(r,2) for r in ratios]})",
                     all(0.45 <= r <= 0.55 for r in ratios)))

with open(f"{out}/checks.txt", "w") as f:
    for label, ok in results:
        f.write(("PASS  " if ok else "FAIL  ") + label + "\n")
    f.write("__ALLPASS__\n" if all(ok for _, ok in results) else "__SOMEFAIL__\n")
PYEOF

if [ -f "$OUT/checks.txt" ]; then
    while IFS= read -r line; do
        case "$line" in
            PASS*) PASS+=("${line#PASS  }") ;;
            FAIL*) FAIL+=("${line#FAIL  }") ;;
        esac
    done < "$OUT/checks.txt"
fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
