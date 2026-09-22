#!/usr/bin/env python3
"""Singer planar difference set of order q=31 in Z_993, then pick the multiplier
whose cyclic gap is largest."""
from math import gcd
q = 31
v = q*q + q + 1          # 993

def find_field():
    # find irreducible monic cubic x^3 = a2 x^2 + a1 x + a0  over GF(q) with x primitive
    for a0 in range(1, q):
        for a1 in range(q):
            for a2 in range(q):
                # irreducible iff no root in GF(q)
                if any((t*t*t - a2*t*t - a1*t - a0) % q == 0 for t in range(q)):
                    continue
                yield (a0, a1, a2)

def mul(u, w, a0, a1, a2):
    # u,w are 3-tuples
    r = [0]*5
    for i in range(3):
        if u[i]==0: continue
        for j in range(3):
            r[i+j] = (r[i+j] + u[i]*w[j]) % q
    # reduce x^4, x^3 using x^3 = a2 x^2 + a1 x + a0
    for d in (4, 3):
        c = r[d]
        if c:
            r[d] = 0
            r[d-1] = (r[d-1] + c*a2) % q
            r[d-2] = (r[d-2] + c*a1) % q
            r[d-3] = (r[d-3] + c*a0) % q
    return (r[0], r[1], r[2])

def order_is_full(a0,a1,a2):
    n = q**3 - 1
    g = (0,1,0)
    # check g^(n/p) != 1 for each prime p | n
    for p in (2,3,5,331):
        e = n//p
        # fast pow
        res=(1,0,0); base=g; ee=e
        while ee:
            if ee&1: res=mul(res,base,a0,a1,a2)
            base=mul(base,base,a0,a1,a2); ee>>=1
        if res==(1,0,0): return False
    return True

params=None
for (a0,a1,a2) in find_field():
    if order_is_full(a0,a1,a2):
        params=(a0,a1,a2); break
a0,a1,a2 = params
print("field: x^3 = %d x^2 + %d x + %d ; x is primitive" % (a2,a1,a0))

D=set()
cur=(1,0,0)
for i in range(q**3-1):
    if cur[2]==0:            # linear functional: coefficient of x^2 vanishes
        D.add(i % v)
    cur = mul(cur,(0,1,0),a0,a1,a2)
D=sorted(D)
print("difference set size:", len(D))
# check planarity
diffs={}
ok=True
for x in D:
    for y in D:
        if x!=y:
            d=(x-y)%v
            diffs[d]=diffs.get(d,0)+1
bad=[d for d in range(1,v) if diffs.get(d,0)!=1]
print("planar (every nonzero residue exactly once):", not bad)

def maxgap(S):
    S=sorted(S); g=0; arg=None
    for i in range(len(S)):
        d = (S[(i+1)%len(S)] - S[i]) % v
        if i==len(S)-1: d = S[0]+v-S[-1]
        if d>g: g=d; arg=i
    return g, arg

best=(0,None,None)
for t in range(1,v):
    if gcd(t,v)!=1: continue
    S=sorted((t*x)%v for x in D)
    g,arg=maxgap(S)
    if g>best[0]: best=(g,t,S)
g,t,S=best
print("best multiplier t=%d  max cyclic gap=%d  -> N = %d" % (t,g,5957+g))
# rotate so the big gap wraps: start right after the gap
S=sorted(S)
i = max(range(len(S)), key=lambda i: (S[(i+1)%len(S)]-S[i])%v if i<len(S)-1 else S[0]+v-S[-1])
start = S[i+1] if i<len(S)-1 else S[0]
P = sorted(((x - start) % v) for x in S)
print("window:", P[-1], " (need <= 784 for N=6166)")
open("P.txt","w").write(" ".join(map(str,P)))
