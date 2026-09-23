# Bose affine difference set: q=2^e, GF(q^2)=GF(2^(2e)), B={i: a^i + a in GF(q)} mod q^2-1
import sys
e=int(sys.argv[1]) if len(sys.argv)>1 else 5
q=1<<e; n=2*e; N=(1<<n)-1
def mul(a,b,poly):
    r=0
    while b:
        if b&1: r^=a
        b>>=1; a<<=1
        if a>>n: a^=poly
    return r
def isprim(poly):
    x=1; 
    for i in range(1,N+1):
        x=mul(x,2,poly)
        if x==1: return i==N
    return False
poly=next(p for p in range(1<<n|1,1<<(n+1),2) if isprim(p))
# GF(q) subfield = {0} U {a^(k*(q+1))}
pw=[1]
for i in range(N-1): pw.append(mul(pw[-1],2,poly))
sub={0}|{pw[(k*(q+1))%N] for k in range(q-1)}
B=sorted(i for i in range(N) if (pw[i]^2) in sub)
m=N
cnt=[0]*m
for a in B:
    for b in B:
        if a!=b: cnt[(a-b)%m]+=1
miss=[r for r in range(1,m) if cnt[r]==0]
assert len(B)==q and max(cnt)==1 and all(r%(q+1)==0 for r in miss), (len(B),max(cnt))
print(m,' '.join(map(str,B)))
