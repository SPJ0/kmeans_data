# Independent verifier: python3 verify.py file  (one integer per line)
import sys
toks=open(sys.argv[1]).read().split()
vals=[int(t) for t in toks]            # raises if non-integer token
import re
assert all(re.fullmatch(r"[0-9]+",t) for t in toks), "non-integer or negative token"
S=set(vals)
N=6166
print("tokens:",len(vals)," distinct:",len(S))
ok=True
if len(S)!=len(vals): print("FAIL: duplicates"); ok=False
if len(S)>128: print("FAIL: more than 128 elements"); ok=False
if min(S)<0: print("FAIL: negative element"); ok=False
L=sorted(S); D=set()
for i in range(len(L)):
    for j in range(i+1,len(L)): D.add(L[j]-L[i])
missing=[d for d in range(1,N+1) if d not in D]
print("missing distances in 1..%d:"%N, len(missing), missing[:20])
if missing: ok=False
print("min",min(S),"max",max(S))
print("VERIFIED" if ok else "NOT VERIFIED")
