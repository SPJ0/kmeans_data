#!/usr/bin/env bash
# One-shot resume after a box pause: all fleets skip cells that already have
# certificates (cell_*.out), so nothing is lost but in-flight work.
set -euo pipefail
cd "$(dirname "$0")"
git -C .. pull --ff-only || true
nohup setsid python3 fleet.py "${1:-32}" 16 > fleet_resume.log 2>&1 < /dev/null &
nohup setsid nice -n 10 python3 jc2_fleet.py 8 17 > jc2_fleet_B17.log 2>&1 < /dev/null &
nohup setsid nice -n 12 python3 jc2_sym_fleet.py 6 17 32 > jc2_sym_fleet.log 2>&1 < /dev/null &
nohup setsid nice -n 8 python3 dc_sym_fleet.py 5 17 24 > dc_sym_fleet.log 2>&1 < /dev/null &
sleep 5
echo "--- fleets:"; pgrep -af "fleet.py|jc2_fleet|jc2_sym_fleet|dc_sym_fleet" | head
echo "--- resume banners:"
head -1 fleet_resume.log jc2_fleet_B17.log jc2_sym_fleet.log dc_sym_fleet.log

# Mixed-coset construction shots (too big for the Mac; run on the box):
nohup bash -c '
python3 jc2_construct.py 51 102 153 dx 1,2
python3 jc2_construct.py 55 110 165 dx 1,3
python3 jc2_construct.py 51 102 153 dx 1,2 2 -1
python3 jc2_construct.py 51 102 153 dy 1,2
' > construct_mixed_box.log 2>&1 &
