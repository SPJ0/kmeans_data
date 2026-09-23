# analyze a leech_sa param line: window contributions, overlaps, waste
import sys,re
line=sys.argv[1]; base=sys.argv[2] if len(sys.argv)>2 else 'out/singer31.txt'
u=int(re.search(r'u (\d+)',line).group(1))
c=list(map(int,re.search(r'c ([\d ]+)\|',line).group(1).split()))
t=list(map(int,re.search(r't ([-\d ]+)$',line.strip()).group(1).split()))
toks=open(base).read().split(); m=int(toks[0]); B=list(map(int,toks[1:]))
X=[[ (u*b+ci)%m+ti for b in B] for ci,ti in zip(c,t)]
N=6166
from collections import defaultdict
who=defaultdict(set)
for i in range(4):
    for j in range(4):
        for x in X[i]:
            for y in X[j]:
                d=x-y
                if d>0: who[d].add((i,j))
cov=set(d for d in who if d<=N)
print("covered",len(cov),"missing",N-len(cov))
miss=[d for d in range(1,N+1) if d not in cov]; print("missing:",miss)
for i in range(4):
  for j in range(4):
    vals=set(x-y for x in X[i] for y in X[j] if x-y>0)
    if not vals: continue
    inr=[v for v in vals if v<=N]; uniq=[v for v in inr if len(who[v])==1]
    print((i,j),"vals",len(vals),"in range",len(inr),"unique",len(uniq),"min",min(vals),"max",max(vals))
