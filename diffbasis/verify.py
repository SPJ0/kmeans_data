#!/usr/bin/env python3
"""Independent verifier for a difference basis covering 1..N with at most K elements."""
import sys

def verify(path, K=128, N=6166, verbose=True):
    txt = open(path).read().replace(',', ' ').split()
    B = [int(x) for x in txt]
    ok = True
    msgs = []
    # 1. integrality / nonnegativity
    if any(b < 0 for b in B):
        ok = False; msgs.append("FAIL: negative element present")
    # 2. distinctness and count
    if len(set(B)) != len(B):
        ok = False; msgs.append("FAIL: duplicate elements")
    if len(set(B)) > K:
        ok = False; msgs.append(f"FAIL: {len(set(B))} distinct elements > {K}")
    S = sorted(set(B))
    # 3. coverage
    seen = bytearray(N + 1)
    for i in range(len(S)):
        for j in range(i + 1, len(S)):
            d = S[j] - S[i]
            if 1 <= d <= N:
                seen[d] = 1
    missing = [d for d in range(1, N + 1) if not seen[d]]
    if missing:
        ok = False
        msgs.append(f"FAIL: {len(missing)} distances uncovered, e.g. {missing[:10]}")
    if verbose:
        print(f"file            : {path}")
        print(f"count           : {len(S)} distinct elements (limit {K})")
        print(f"all nonneg ints : {all(isinstance(b,int) and b>=0 for b in S)}")
        print(f"min / max       : {S[0]} / {S[-1]}")
        print(f"pairs available : {len(S)*(len(S)-1)//2}")
        print(f"target range    : 1..{N}")
        print(f"uncovered count : {len(missing)}")
        for m in msgs: print(m)
        print("RESULT          :", "PASS - valid difference basis" if ok else "FAIL")
    return ok, len(missing)

if __name__ == "__main__":
    p = sys.argv[1]
    K = int(sys.argv[2]) if len(sys.argv) > 2 else 128
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 6166
    ok, _ = verify(p, K, N)
    sys.exit(0 if ok else 1)
