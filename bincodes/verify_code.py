#!/usr/bin/env python3
"""Independent verifier for a binary constant-length code.
Usage: verify_code.py <file> <expected_count> <length> <min_distance>
Checks: length of every string, binary alphabet, distinctness, exact count,
and the Hamming distance of EVERY pair (computed character by character)."""
import sys
from itertools import combinations

path, want_count, want_len, want_d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
lines = [ln.strip() for ln in open(path) if ln.strip() != ""]

problems = []
# 1. lengths
bad_len = [s for s in lines if len(s) != want_len]
if bad_len: problems.append(f"{len(bad_len)} string(s) not length {want_len}: {bad_len[:3]}")
# 2. alphabet
bad_sym = [s for s in lines if set(s) - {"0", "1"}]
if bad_sym: problems.append(f"{len(bad_sym)} string(s) contain non-binary symbols: {bad_sym[:3]}")
# 3. distinctness
if len(set(lines)) != len(lines):
    dup = sorted({s for s in lines if lines.count(s) > 1})
    problems.append(f"duplicate string(s): {dup[:5]}")
# 4. count
if len(lines) != want_count:
    problems.append(f"expected exactly {want_count} strings, found {len(lines)}")
# 5. pairwise distances, char by char
pairs = 0; mind = None; worst = None
hist = {}
for a, b in combinations(lines, 2):
    if len(a) != len(b): continue
    d = sum(1 for x, y in zip(a, b) if x != y)
    pairs += 1
    hist[d] = hist.get(d, 0) + 1
    if mind is None or d < mind: mind, worst = d, (a, b)
if mind is not None and mind < want_d:
    problems.append(f"minimum pairwise distance {mind} < {want_d}, e.g. {worst}")

print(f"file                  : {path}")
print(f"strings found         : {len(lines)} (required exactly {want_count})")
print(f"all length {want_len}          : {not bad_len}")
print(f"all symbols in {{0,1}}   : {not bad_sym}")
print(f"all distinct          : {len(set(lines)) == len(lines)}")
print(f"pairs checked         : {pairs} (expected {want_count*(want_count-1)//2})")
print(f"minimum distance      : {mind} (required >= {want_d})")
print(f"distance distribution : {dict(sorted(hist.items()))}")
for p in problems: print("FAIL:", p)
print("RESULT                :", "PASS" if not problems else "FAIL")
sys.exit(0 if not problems else 1)
