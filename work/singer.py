# Build a Singer perfect difference set mod m=q^2+q+1 for prime q.
import sys, itertools
q = int(sys.argv[1]) if len(sys.argv)>1 else 31
m = q*q+q+1
def mulmod(a,b,poly):  # elements as tuples (c0,c1,c2), poly x^3 = p0 + p1 x + p2 x^2
    r=[0]*5
    for i in range(3):
        for j in range(3): r[i+j]+=a[i]*b[j]
    for k in (4,3):
        c=r[k]; r[k]=0
        for i in range(3): r[k-3+i]+=c*poly[i]
    return tuple(x%q for x in r[:3])
N=q**3-1
def order_ok(poly):
    # check x is primitive: x^(N/p) != 1 for prime p|N
    fac=[];n=N;p=2
    while p*p<=n:
        if n%p==0: fac.append(p)
        while n%p==0: n//=p
        p+=1
    if n>1: fac.append(n)
    def pw(e):
        res=(1,0,0);b=(0,1,0)
        while e:
            if e&1: res=mulmod(res,b,poly)
            b=mulmod(b,b,poly);e>>=1
        return res
    if pw(N)!=(1,0,0): return False
    return all(pw(N//p)!=(1,0,0) for p in fac)
for p0 in range(1,q):
  for p1 in range(q):
    poly=(p0,p1,0)
    if order_ok(poly): break
  else: continue
  break
x=(1,0,0);D=[]
for i in range(m):
    if x[2]==0: D.append(i)
    x=mulmod(x,(0,1,0),poly)
D=sorted(D)
# verify perfect
cnt=[0]*m
for a in D:
    for b in D:
        if a!=b: cnt[(a-b)%m]+=1
assert len(D)==q+1 and all(c==1 for c in cnt[1:]), (len(D))
print(m, ' '.join(map(str,D)))
