#!/usr/bin/env bash
# Verifies mixer wiring via file_poly per-voice outlets (mixer-wiring item):
# file_poly 2-5 -> mixer 0-3 -> master dry sum, with vol isolation and
# wet via send (DC to dodge the one-block send~ lag). Timeline in
# test_mixer_via_file_poly.pd (builders/build_test_mixer_via_file_poly.py).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mix-via-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/cap.wav" "$OUT/cap2.wav"

python3 mlrv-pd/tests/gen_test_wav.py /tmp/mix_const0.wav 4000 const 16000 || exit 1
python3 mlrv-pd/tests/gen_test_wav.py /tmp/mix_const1.wav 4000 const 8000 || exit 1

timeout 8 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mixer_via_file_poly.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
ok() { PASS+=("$1"); }
bad() { FAIL+=("$1"); }

if grep -qi "error:" "$OUT/pd.log" | grep -v "ALSA"; then bad "no pd errors"; else ok "no pd errors"; fi

python3 - <<'PYEOF' > "$OUT/peaks.txt" 2>&1
import struct, wave
def peak(path):
    w=wave.open(path); n=w.getnframes(); d=w.readframes(n); w.close()
    ss=struct.unpack("<%dh"%n, d)
    return max(abs(s) for s in ss)
print("mix", peak("/tmp/mix_via_cap.wav"))
print("mix2", peak("/tmp/mix_via_cap2.wav"))
print("sum", peak("/tmp/mix_sum_cap.wav"))
PYEOF
cat "$OUT/peaks.txt"
MIX="$(grep '^mix ' "$OUT/peaks.txt" | awk '{print $2}')"
MIX2="$(grep '^mix2' "$OUT/peaks.txt" | awk '{print $2}')"
SUM="$(grep '^sum' "$OUT/peaks.txt" | awk '{print $2}')"
if [ -n "$MIX" ] && [ "$MIX" -ge 22000 ] && [ "$MIX" -le 25000 ]; then ok "mix first capture 24000 peak $MIX"; else bad "mix first peak $MIX want 22000-25000"; fi
if [ -n "$MIX2" ] && [ "$MIX2" -ge 8500 ] && [ "$MIX2" -le 10000 ]; then ok "vol isolation: mixer dry peak $MIX2 ~9334 (voice0 muted, master tanh)"; else bad "mix2 peak $MIX2 want 8500-10000"; fi
if [ -n "$SUM" ] && [ "$SUM" -ge 22000 ] && [ "$SUM" -le 25000 ]; then ok "legacy sum still 24000 (pre-mixer) peak $SUM"; else bad "sum peak $SUM want 22000-25000"; fi

# query dump from mixer outlet 1
if grep -q "mix_rep: vol 0 0" "$OUT/pd.log" && grep -q "mix_rep: vol 1 1" "$OUT/pd.log"; then ok "mixer query shows vols 0,1"; else bad "mixer query"; fi

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
