# Construction: X = lift of multiplier-629 image of Singer set (q=31, m=993), cut at gap 7;
# B = X + 993*{0,1,4,6}  (Leech-style product with perfect ruler {0,1,4,6}).
toks=open('out/singer31.txt').read().split(); m=int(toks[0]); Bs=list(map(int,toks[1:]))
u,g=629,7
S=sorted((u*b)%m for b in Bs)
X=sorted((s-S[g])%m for s in S)
A=sorted(x+m*t for t in (0,1,4,6) for x in X)
open('solution.txt','w').write('\n'.join(map(str,A))+'\n')
print(len(A), A[:10], A[-3:])
