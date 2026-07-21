#!/usr/bin/env bash
# One-shot bootstrap for the Dixmier B=16 fleet on a big machine (32+ cores).
# Usage: bash bootstrap.sh [ncores]
set -euo pipefail
cd "$(dirname "$0")"
NCORES="${1:-$(nproc)}"

echo "== installing toolchain (micromamba + msolve + sympy) =="
if [ ! -x ./mm/bin/msolve ]; then
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj bin/micromamba
  ./bin/micromamba create -y -p ./mm -c conda-forge msolve python=3.12 sympy
fi
export PATH="$PWD/mm/bin:$PATH"
msolve -h >/dev/null 2>&1 || { echo "msolve install failed"; exit 1; }
echo "msolve OK; python: $(./mm/bin/python -V); cores: $NCORES"

echo "== launching fleet =="
nohup ./mm/bin/python fleet.py "$NCORES" > fleet.log 2>&1 &
echo "fleet running in background; tail -f dixmier/fleet.log"
echo "verdicts accumulate in dixmier/results.log; when done, commit & push that file."
