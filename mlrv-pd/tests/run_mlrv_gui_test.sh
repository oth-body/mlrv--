#!/usr/bin/env bash
# Increment-2 verification (1:1 mlrv recreation, item 5 mapping GUI): the
# identical bytes GUI widgets emit, sent headlessly, driving the REAL
# engine with captured-audio proof, plus a live-UDP OSC leg and a clean
# load of mlrv-gui.pd itself (widgets + engine + all 3 adapters).
#
# A. mapper path: learn vgain1 + ctl -> `gain 1 0.5` -> real file_poly
#    const-16000 loop -> capture peak ~8000.
# B. OSC leg: real UDP /mlrv/ctl packet -> osc_ctl -> mapper (sgroup0
#    bound) -> exact `group 0 2` dispatch.
# C. widget-direct path: literal `gain 1 0.5` bytes -> same assert as A.
# D. mode widget bytes: `mode 1 shot` -> burst then silence over a
#    2-period window (loop would repeat).
# E. mlrv-gui.pd loads clean (ALSA-no-device notice tolerated, real
#    errors fail).
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-gui-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log" "$OUT/osc.log" "$OUT/gui.log"

python3 mlrv-pd/tests/gen_test_wav.py /tmp/mlrv_gui_const.wav 4410 const 16000 || exit 1

timeout 12 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_mlrv_gui.pd > "$OUT/pd.log" 2>&1 &
PD_PID=$!
sleep 4.3
send_osc() {
python3 -c "
import socket, struct
def pstr(s):
    b = s.encode() + b'\x00'
    return b + b'\x00' * ((4 - len(b) % 4) % 4)
pkt = pstr('/mlrv/ctl') + pstr(',if') + struct.pack('>i', 20) + struct.pack('>f', 0.6)
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(pkt, ('127.0.0.1', 9007))
"
}
send_osc >> "$OUT/osc.log" 2>&1
sleep 0.5
send_osc >> "$OUT/osc.log" 2>&1
wait "$PD_PID"

timeout 8 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    -path mlrv-pd/samples mlrv-pd/mlrv-gui.pd > "$OUT/gui.log" 2>&1

PASS=()
FAIL=()
ok()  { PASS+=("$1"); }
bad() { FAIL+=("$1"); }

if grep -qi "error:" "$OUT/pd.log"; then bad "test patch: no pd errors"; else ok "test patch: no pd errors"; fi
if grep -v "ALSA" "$OUT/gui.log" | grep -qi "error:"; then bad "mlrv-gui.pd loads clean"; else ok "mlrv-gui.pd loads clean (widgets+engine+adapters)"; fi

DISP="$(grep -o '^disp: .*' "$OUT/pd.log" | sed 's/^disp: //' | tr '\n' '|')"
[ "$DISP" = "gain 1 0.5|group 0 2|" ] && ok "dispatch bytes exact (mapper gain, OSC group)" || bad "dispatch: '$DISP'"

python3 - <<'EOF' > "$OUT/peaks.txt" 2>&1
import struct, wave
def peak(path, a=None, b=None):
    w = wave.open(path)
    n = w.getnframes()
    ss = struct.unpack("<%dh" % n, w.readframes(n))
    w.close()
    a = 0 if a is None else int(a * n)
    b = n if b is None else int(b * n)
    return max(abs(s) for s in ss[a:b])
print("capA", peak("/tmp/mlrv_gui_capA.wav"))
print("capB", peak("/tmp/mlrv_gui_capB.wav"))
print("capD1", peak("/tmp/mlrv_gui_capD.wav", 0, 0.5))
print("capD2", peak("/tmp/mlrv_gui_capD.wav", 0.5, 1))
EOF
cat "$OUT/peaks.txt"
PA="$(grep '^capA' "$OUT/peaks.txt" | awk '{print $2}')"
PB="$(grep '^capB' "$OUT/peaks.txt" | awk '{print $2}')"
PD1="$(grep '^capD1' "$OUT/peaks.txt" | awk '{print $2}')"
PD2="$(grep '^capD2' "$OUT/peaks.txt" | awk '{print $2}')"
if [ "$PA" -ge 7200 ] && [ "$PA" -le 8800 ]; then ok "mapper gain path audio: peak $PA (~8000)"; else bad "capA peak $PA (want 7200-8800)"; fi
if [ "$PB" -ge 7200 ] && [ "$PB" -le 8800 ]; then ok "widget-direct gain audio: peak $PB (~8000)"; else bad "capB peak $PB (want 7200-8800)"; fi
if [ "$PD1" -ge 5000 ] && [ "$PD2" -lt 1000 ]; then ok "shot mode: burst $PD1 then silence $PD2"; else bad "shot halves: $PD1 / $PD2"; fi

echo "---- checks (audio asserts run inline next)"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
