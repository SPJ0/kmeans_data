# rebuild set from a leech_sa log line: python3 rebuild.py "<line>" outfile
import sys,re
line=sys.argv[1]
u=int(re.search(r'u (\d+)',line).group(1))
c=list(map(int,re.search(r'c ([\d ]+)\|',line).group(1).split()))
t=list(map(int,re.search(r't ([-\d ]+)$',line.strip()).group(1).split()))
toks=open('out/singer31.txt').read().split(); m=int(toks[0]); B=list(map(int,toks[1:]))
A=sorted(set((u*b+ci)%m+ti for ci,ti in zip(c,t) for b in B))
mn=min(A); A=[a-mn for a in A]
open(sys.argv[2],'w').write('\n'.join(map(str,A))+'\n'); print(len(A))
