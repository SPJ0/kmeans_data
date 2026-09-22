import sys
def wich(r,s):
    segs = [1]*r + [r+1] + [2*r+1]*r + [4*r+3]*(s+1) + [2*r+2]*(r+1) + [1]*r
    m=[0]
    for g in segs: m.append(m[-1]+g)
    return m
best=None
for r in range(1,40):
    for s in range(0,120):
        m=wich(r,s)
        if len(m)<=128:
            if best is None or m[-1]>best[-1]: best=m; br,bs=r,s
print("marks",len(best),"len",best[-1],"r,s",br,bs)
open("wichmann.txt","w").write(" ".join(map(str,best)))
