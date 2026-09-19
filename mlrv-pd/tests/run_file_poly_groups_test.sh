#!/usr/bin/env bash
# Verifies file_poly.pd's new `group <slot 0-7> <groupNum>` message: real
# assignment, reassignment (last-write-wins), the deliberate default (an
# untouched slot reads group 0 = ungrouped), and out-of-range gating (a
# bad slot number is discarded, not clamped onto a neighboring slot).
#
# This is increment 1 of 2 for the mute-group item (1:1 mlrv recreation
# track) -- storage only. Exclusivity behavior (a new trigger silencing
# a group-mate) and `groupstop` are increment 2, tested separately.
#
# Exit 0 on all checks passing, 1 otherwise.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${TMPDIR:-/tmp}/mlrv-fpgroups-test"
mkdir -p "$OUT"
rm -f "$OUT/pd.log"

timeout 3 pd -nogui -stderr -path mlrv-pd/abstractions -path mlrv-pd/patchers \
    mlrv-pd/tests/test_file_poly_groups.pd > "$OUT/pd.log" 2>&1

PASS=()
FAIL=()
check_no_errors() {
    if grep -qi "error:" "$OUT/pd.log"; then FAIL+=("no pd errors"); else PASS+=("no pd errors"); fi
}
check_no_errors

check_val() {  # check_val <label> <pattern>
    if grep -q -- "$2" "$OUT/pd.log"; then PASS+=("$1"); else FAIL+=("$1"); fi
}
check_val "slot 0 assigned group 2"                    "slot0_group: 2"
check_val "slot 3 reassigned to group 0 (last write wins)" "slot3_group: 0"
check_val "slot 5 never touched, defaults to 0 (ungrouped)" "slot5_group: 0"
check_val "out-of-range slot 9 write didn't corrupt slot 7" "slot7_group: 0"

echo "---- checks"
for c in "${PASS[@]}"; do echo "PASS  $c"; done
for c in "${FAIL[@]}"; do echo "FAIL  $c"; done

[ "${#FAIL[@]}" -eq 0 ]
