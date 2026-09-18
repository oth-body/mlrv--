#!/usr/bin/env bash
# Verifies mixer.pd end to end against exact expected signals.
#
# Four fixtures, all sized to exactly one loop period (4410 samples) so a
# full-window capture's MEAN is phase-independent (the capture always spans
# one complete cycle regardless of exactly when in real time it started) --
# this sidesteps needing to track exact playback phase across independently
# scheduled real-time trigger messages, while a wrong voice->gain mapping
# still breaks the expected sum immediately: v0/v1 are DISTINCT const DC
# levels, v2/v3 are DISTINCT-peak ramps (mean ~0, so they contribute to the
# SPAN but not the mean -- confirms ramps are genuinely live, not flattened).
#
# Windows: dry1 (vol=[1,.5,.25,.5], send=0) -> vol0=0.5,send0=0.3 -> wet
# (only v0, a const, contributes -- so this window is exact even without a
# lag-aligned capture) -> vol3=0.75 -> dry2. Two dry windows with different
# gains rules out a coincidental compensating-error pass.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-mixer-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT"/*.wav /tmp/mlrv_mix_v*.wav /tmp/mlrv_mix_cap_*.wav

N=4410
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/v0.wav" "$N" const 16000 || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/v1.wav" "$N" const 8000  || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/v2.wav" "$N" ramp  12000 || exit 1
python3 mlrv-pd/tests/gen_test_wav.py "$OUT/v3.wav" "$N" ramp  4000  || exit 1

# test_mixer.pd hardcodes these paths -- keep in sync.
for i in 0 1 2 3; do cp "$OUT/v$i.wav" "/tmp/mlrv_mix_v$i.wav"; done

timeout 7 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mixer.pd > "$OUT/pd.log" 2>&1
for c in dry1 wet dry2; do cp "/tmp/mlrv_mix_cap_$c.wav" "$OUT/cap_$c.wav" 2>/dev/null; done

PASS=()
FAIL=()

check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

for c in dry1 wet dry2; do
    if [ -s "$OUT/cap_$c.wav" ]; then PASS+=("capture cap_$c written"); else FAIL+=("capture cap_$c written"); fi
done

PYOUT="$(python3 - "$OUT" <<'EOF'
import struct, sys, wave

outdir = sys.argv[1]
rows = []
ok = lambda cond, msg: (f"PASS {msg}" if cond else f"FAIL {msg}", cond)


def read_wav(name):
    try:
        with wave.open(f"{outdir}/{name}", "rb") as w:
            data = w.readframes(w.getnframes())
            return struct.unpack("<" + str(w.getnframes()) + "h", data)
    except FileNotFoundError:
        return None


def check_mean(name, exp, tol=6):
    got = read_wav(name)
    if got is None:
        rows.append(ok(False, f"{name}: wav written"))
        return None
    mean = sum(got) / len(got)
    good = abs(mean - exp) <= tol
    rows.append(ok(good, f"{name} mean {mean:.1f} (expect {exp}, tol {tol})"))
    return got


# dry1: v0*1 + v1*0.5 + v2ramp*0.25(mean~0) + v3ramp*0.5(mean~0) = 16000 + 4000 = 20000
got_d1 = check_mean("cap_dry1.wav", 20000, tol=6)

# wet: only v0 (const 16000) contributes, post-vol(0.5)*send(0.3) = 2400.
# v0 is DC, so this is exact regardless of the send~/receive~ cross-block lag
# (gotcha 16) -- shifting a constant signal in time doesn't change its value.
got_w = check_mean("cap_wet.wav", 2400, tol=6)
if got_w is not None:
    span = max(got_w) - min(got_w)
    good = span <= 4
    rows.append(ok(good, f"cap_wet flat (span {span}, expect ~0 -- confirms only "
                      "the DC send-armed voice contributes)"))

# dry2: v0*0.5 + v1*0.5 + v2ramp*0.25 + v3ramp*0.75(mean~0) = 8000 + 4000 = 12000
got_d2 = check_mean("cap_dry2.wav", 12000, tol=6)

# span sanity: dry windows must show real variation from the two live ramps,
# not be flattened by a bug that zeroed v2/v3's contribution.
if got_d1 is not None:
    span1 = max(got_d1) - min(got_d1)
    good = span1 > 5000
    rows.append(ok(good, f"cap_dry1 span {span1} > 5000 (ramps genuinely live)"))
if got_d2 is not None:
    span2 = max(got_d2) - min(got_d2)
    good = span2 > 5000
    rows.append(ok(good, f"cap_dry2 span {span2} > 5000 (ramps genuinely live)"))

# gain-change sanity: dry2's vol0 dropped (1->0.5) and vol3 rose (.5->.75) vs
# dry1 -- the two means must differ, ruling out a control message that never
# actually reached the mixer.
if got_d1 is not None and got_d2 is not None:
    m1, m2 = sum(got_d1) / len(got_d1), sum(got_d2) / len(got_d2)
    good = abs(m1 - m2) > 1000
    rows.append(ok(good, f"dry1 mean {m1:.0f} != dry2 mean {m2:.0f} "
                      "(vol changes took effect)"))

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
