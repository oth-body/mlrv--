#!/usr/bin/env bash
# Verifies reverb_fx~.pd against real captured audio (not just a clean
# load): unlike delay's discrete echoes, a real FDN reverb's impulse
# response is dense and noise-like, so this checks windowed RMS ENERGY
# DECAY over time rather than discrete peak regions.
#   - cap1 (liveness=90): energy must decay smoothly and still be clearly
#     non-silent 1200ms after a 2.3ms burst -- proof of a genuine long
#     reverb tail, not a burst passthrough.
#   - cap2 (liveness=10, burst fired 1900ms after burst1): energy at the
#     same 500ms offset must be dramatically lower than cap1's -- proof
#     the liveness parameter genuinely controls decay time.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-reverb-fx-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" /tmp/mlrv_rfx_burst.wav /tmp/mlrv_rfx_cap1.wav /tmp/mlrv_rfx_cap2.wav

python3 mlrv-pd/tests/gen_test_wav.py /tmp/mlrv_rfx_burst.wav 100 const 16000 || exit 1

# rev3~ is CPU-heavy (2-in/4-out feedback delay network) -- headroom
# beyond the plain send~/receive~ tests' usual 6s timeout is needed for
# the full 3.8s virtual timeline to complete under -nogui.
timeout 20 pd -nogui -stderr -path mlrv-pd/abstractions \
    mlrv-pd/tests/test_reverb_fx.pd > "$OUT/pd.log" 2>&1

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

def windowed_rms(samples, sr, win_ms=100):
    win = int(sr * win_ms / 1000)
    out = []
    for i in range(0, len(samples) - win, win):
        chunk = samples[i:i+win]
        rms = (sum(s*s for s in chunk) / len(chunk)) ** 0.5
        out.append(rms)
    return out

results = []

s1, sr1 = load("/tmp/mlrv_rfx_cap1.wav")
w1 = windowed_rms(s1, sr1)
results.append((f"cap1: non-silent immediately after burst (rms {w1[0]:.1f})", w1[0] > 100))
results.append((f"cap1: still clearly non-silent at 1200ms -- genuine long tail (rms {w1[12]:.1f})",
                 w1[12] > 5))
# monotonic-ish decay: allow small local bumps but overall must trend down hard
results.append((f"cap1: energy decays overall (rms[0]={w1[0]:.1f} > rms[10]={w1[10]:.1f} > rms[12]={w1[12]:.1f})",
                 w1[0] > w1[10] > w1[12]))

s2, sr2 = load("/tmp/mlrv_rfx_cap2.wav")
w2 = windowed_rms(s2, sr2)
results.append((f"cap2: non-silent immediately after burst (rms {w2[0]:.1f})", w2[0] > 100))
results.append((f"cap2 (liveness=10) decays MUCH faster than cap1 (liveness=90) at 500ms: "
                 f"cap1={w1[5]:.1f} vs cap2={w2[5]:.1f}", w2[5] < w1[5] / 10))

with open(f"{out}/checks.txt", "w") as f:
    for label, ok in results:
        f.write(("PASS  " if ok else "FAIL  ") + label + "\n")
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
