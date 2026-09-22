#!/bin/bash
# one worker: RLE search -> extract marks -> RnR polish -> keep best
cd /home/user/kmeans_data/diffbasis
W=$1; N=${2:-6166}; TB=${3:-60}; TP=${4:-60}
mkdir -p runs/w$W
best=999999
[ -f runs/w$W/best.txt ] && best=$(python3 -c "
import sys;sys.path.insert(0,'.')
from verify import verify
print(verify('runs/w$W/best.txt',128,$N,False)[1])" 2>/dev/null || echo 999999)
while true; do
  S=$((6 + RANDOM % 9))
  SD=$RANDOM
  ./blocks 128 $N $TB $SD $S > runs/w$W/rle.txt 2>/dev/null
  sed -n 3p runs/w$W/rle.txt > runs/w$W/seed.txt
  ./rnr 128 $N 7200 $TP $SD runs/w$W/seed.txt runs/w$W/pol.txt > runs/w$W/m.txt 2>/dev/null
  m=$(cat runs/w$W/m.txt)
  if [ "$m" -lt "$best" ] 2>/dev/null; then best=$m; cp runs/w$W/pol.txt runs/w$W/best.txt; echo "$(date +%T) w$W new best $m" >> runs/progress.log; fi
  if [ "$m" -eq 0 ] 2>/dev/null; then cp runs/w$W/pol.txt runs/SOLVED.txt; echo SOLVED >> runs/progress.log; break; fi
done
