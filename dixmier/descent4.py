import sympy as sp, time, pickle, sys
from sympy.polys.rings import ring
from sympy import QQ

t0=time.time()
# --- generators: p-vars then q-vars ---
pspec=[(16,8),(0,16),(-16,8),(-32,0)]
qspec=[(32,8),(16,16),(0,24),(-16,16),(-32,8),(-48,0)]
pnames=[f'p_{w}_{j}' for w,db in pspec for j in range(db+1)]
qnames=[f'q_{w}_{j}' for w,db in qspec for j in range(db+1)]
R, *gens = ring(','.join(pnames+qnames), QQ)
G={n:g for n,g in zip(pnames+qnames,gens)}
NP=len(pnames)
qpos={n:i for i,n in enumerate(pnames+qnames) if n.startswith('q')}

def rc(x):
    if isinstance(x, sp.Rational): return R.ground_new(QQ(int(x.p), int(x.q)))
    return R.ground_new(QQ(x))
ONE=R.one; ZERO=R.zero

# t-polys: python list of R-elems, index = power of t
def tp_add(A,B):
    n=max(len(A),len(B)); return [ (A[i] if i<len(A) else ZERO)+(B[i] if i<len(B) else ZERO) for i in range(n)]
def tp_scale(A,c): return [a*c for a in A]
def tp_mul(A,B):
    out=[ZERO]*(len(A)+len(B)-1)
    for i,a in enumerate(A):
        if a==ZERO: continue
        for j,b in enumerate(B):
            if b==ZERO: continue
            out[i+j]=out[i+j]+a*b
    return out
import math
def tp_shift(A,s):  # t -> t - s
    n=len(A); out=[ZERO]*n
    for k,a in enumerate(A):
        if a==ZERO: continue
        for j in range(k+1):
            out[j]=out[j]+a*rc(math.comb(k,j)*(-s)**(k-j))
    return out
def tp_trim(A):
    while A and A[-1]==ZERO: A=A[:-1]
    return A

def phi(c,shift=0):  # QQ t-poly: prod (t+shift-j), j=0..c-1  -> list of R-elems
    P=[ONE]
    for j in range(c): P=tp_mul(P,[rc(shift-j),ONE])
    return P
def psi(c,shift=0):
    P=[ONE]
    for j in range(1,c+1): P=tp_mul(P,[rc(shift+j),ONE])
    return P
def vmul(w1,w2):
    if w1>=0 and w2>=0: return [ONE]
    if w1<=0 and w2<=0: return [ONE]
    if w1>0 and w2<0:
        c=-w2
        return phi(c,-(w1-c)) if w1>=c else phi(w1)
    c=-w1
    return psi(c) if w2>=c else psi(w2,c-w2)
def emul(e1,e2):
    out={}
    for w1,A in e1.items():
        for w2,B in e2.items():
            term=tp_mul(tp_mul(A,tp_shift(B,w1)),vmul(w1,w2))
            w=w1+w2
            out[w]=tp_add(out.get(w,[ZERO]),term)
    return {w:tp_trim(A) for w,A in out.items() if tp_trim(A)}
def ecomm(a,b):
    m1,m2=emul(a,b),emul(b,a)
    out={}
    for w in set(m1)|set(m2):
        A=tp_add(m1.get(w,[ZERO]),tp_scale(m2.get(w,[ZERO]),rc(-1)))
        A=tp_trim(A)
        if A: out[w]=A
    return out

# self-test vs weyl.py on random small elements
from weyl import t as tsym, comm as wcomm
import random
random.seed(7)
for _ in range(6):
    e1w=random.choice([-2,1]); e2w=random.choice([-1,3])
    c1,c2=random.randint(1,3),random.randint(1,3)
    E1={e1w:[rc(c1),ONE]}; E2={e2w:[rc(c2),ZERO,ONE]}
    S1={e1w:c1+tsym}; S2={e2w:c2+tsym**2}
    got=ecomm(E1,E2); want=wcomm(S1,S2)
    for w in set(got)|set(want):
        gw=got.get(w,[ZERO]); ww=sp.Poly(want.get(w,0),tsym).all_coeffs()[::-1] if want.get(w,0)!=0 else []
        for i in range(max(len(gw),len(ww))):
            a=gw[i] if i<len(gw) else ZERO
            b=QQ(int(ww[i])) if i<len(ww) and ww[i]!=0 else QQ(0)
            assert a==R.ground_new(b), (w,i,a,b)
print(f'ring kernel self-test vs weyl.py: OK [{time.time()-t0:.0f}s]',flush=True)

# --- build cell ---
P={32:[ONE]}
for w,db in pspec: P[w]=[G[f'p_{w}_{j}'] for j in range(db+1)]
Q={48:[ONE]}
for w,db in qspec: Q[w]=[G[f'q_{w}_{j}'] for j in range(db+1)]
C=ecomm(Q,P)
print(f'commutator built in ring [{time.time()-t0:.0f}s]',flush=True)

def subs_linear(pol, i, val):
    # pol linear in gen i: pol = p0 + g_i*p1 -> p0 + p1*val
    p0=R.zero; p1=R.zero
    for mon,coef in pol.terms():
        if mon[i]==0: p0+=R.from_terms([(mon,coef)])
        else:
            m2=list(mon); m2[i]=0
            p1+=R.from_terms([(tuple(m2),coef)])
    return p0+p1*val

determined={}   # gen index -> R-elem
def apply_det(pol):
    for i,v in determined.items():
        # cheap check: does gen i appear?
        if any(m[i] for m,_ in pol.terms()): pol=subs_linear(pol,i,v)
    return pol

order=[(64,32),(48,16),(32,0),(16,-16),(0,-32),(-16,-48)]
constraints=[]
qidx={w:[qpos[f'q_{w}_{j}'] for j in range(db+1)] for w,db in qspec}
for w,u in order:
    eq=[apply_det(c) for c in C.get(w,[])]
    if w==0: eq[0]=eq[0]-ONE
    idxs=qidx[u]; n=len(idxs); rows=len(eq)
    M=sp.zeros(rows,n); rhs=[R.zero]*rows
    for r,pol in enumerate(eq):
        rest=R.zero
        lin={j:QQ(0) for j in range(n)}
        for mon,coef in pol.terms():
            hit=[j for j,gi in enumerate(idxs) if mon[gi]>0]
            if hit:
                j=hit[0]
                m2=list(mon); m2[idxs[j]]-=1
                assert not any(m2[gi] for gi in idxs) and sum(m2)==0, 'nonconstant pivot'
                lin[j]+=coef
            else: rest+=R.from_terms([(mon,coef)])
        for j in range(n): M[r,j]=sp.Rational(int(lin[j].numerator),int(lin[j].denominator))
        rhs[r]=rest*rc(-1)
    # gaussian elimination with QQ pivots, carrying R-elem rhs
    solved={}; r0=0
    rowsM=[[M[r,j] for j in range(n)] for r in range(rows)]
    for col in range(n):
        pr=next((r for r in range(r0,rows) if rowsM[r][col]!=0),None)
        if pr is None: continue
        rowsM[r0],rowsM[pr]=rowsM[pr],rowsM[r0]; rhs[r0],rhs[pr]=rhs[pr],rhs[r0]
        pv=rowsM[r0][col]
        rowsM[r0]=[x/pv for x in rowsM[r0]]; rhs[r0]=rhs[r0]*rc(sp.Rational(1)/pv)
        for r in range(rows):
            if r!=r0 and rowsM[r][col]!=0:
                f=rowsM[r][col]
                rowsM[r]=[a-f*b for a,b in zip(rowsM[r],rowsM[r0])]
                rhs[r]=rhs[r]-rhs[r0]*rc(f)
        solved[col]=r0; r0+=1
    for col,r in solved.items():
        val=rhs[r]-sum((rc(rowsM[r][j])*G[qnames[idxs[j]-NP]] for j in range(n) if j not in solved and rowsM[r][j]!=0),R.zero)
        determined[idxs[col]]=val
    newcons=[rhs[r] for r in range(rows) if all(rowsM[r][j]==0 for j in range(n)) and rhs[r]!=R.zero]
    # re-apply new determinations to previously determined and constraints
    determined={i:apply_det(v) for i,v in determined.items()}
    constraints=[apply_det(c) for c in constraints]+newcons
    constraints=[c for c in constraints if c!=R.zero]
    print(f'level {w:4d}: solved {len(solved)}/{n} of q_{u}, +{len(newcons)} constraints [{time.time()-t0:.0f}s]',flush=True)
for w in sorted(set(C)-{x for x,_ in order}-{80},reverse=True):
    eq=[apply_det(c) for c in C[w]]
    add=[c for c in eq if c!=R.zero]
    constraints+=add
    print(f'level {w:4d}: pure constraints +{len(add)} [{time.time()-t0:.0f}s]',flush=True)
vars_used=sorted(set().union(*[{ (pnames+qnames)[i] for m,_ in c.terms() for i,e in enumerate(m) if e>0} for c in constraints])) if constraints else []
print(f'TOTAL {len(constraints)} constraints, vars: {len(vars_used)} [{time.time()-t0:.0f}s]',flush=True)
pickle.dump(([c.as_expr() for c in constraints],vars_used),open('s16_constraints_ring.pkl','wb'))
print('saved. now groebner...',flush=True)
exprs=[c.as_expr() for c in constraints]
vs=[sp.Symbol(v) for v in vars_used]
Gb=sp.groebner(exprs,*vs,order='grevlex')
print('GROEBNER VERDICT:','EMPTY' if list(Gb.exprs)==[sp.Integer(1)] else f'NONEMPTY basis {len(Gb.exprs)}',flush=True)
if list(Gb.exprs)!=[sp.Integer(1)]:
    for g in list(Gb.exprs)[:10]: print('  ',g)
