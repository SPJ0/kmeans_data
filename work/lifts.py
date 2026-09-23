# enumerate all distinct lifts X (multiplier u, cut gap) of Singer set; report first-gap L of positive differences
import math
toks=open('out/singer31.txt').read().split(); m=int(toks[0]); B=list(map(int,toks[1:]))
seen=set(); res=[]
for u in range(1,m):
    if math.gcd(u,m)!=1: continue
    S=sorted((u*b)%m for b in B)
    key=tuple(S)
    for g in range(32):  # cut just after S[g-1], i.e. start at S[g]
        X=sorted((s-S[g])%m for s in S)
        tX=tuple(X)
        if tX in seen: continue
        seen.add(tX)
        D=set(b-a for i,a in enumerate(X) for b in X[i+1:])
        L=1
        while L in D: L+=1
        res.append((L-1,X[-1],u,g))
res.sort(reverse=True)
print(len(res))
for r in res[:15]: print(r)
