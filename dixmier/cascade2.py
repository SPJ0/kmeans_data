import sympy as sp, time, sys
from weyl import t, mul, comm, clean

def cell_system(d, degP, degQ, corner='extreme'):
    syms=[]
    def make(name, degmax, wrange):
        e={}
        for w in wrange:
            db=(degmax-abs(w))//2
            if db<0: continue
            coeffs=[sp.Symbol(f'{name}_{w}_{j}') for j in range(db+1)]
            syms.extend(coeffs)
            e[w]=sum(c*t**j for j,c in enumerate(coeffs))
        return e
    wP=[w for w in range(-degP,degP+1) if w%d==0]
    wQ=[w for w in range(-degQ,degQ+1) if w%d==0]
    P=make('p',degP,wP); Q=make('q',degQ,wQ)
    C=comm(Q,P)
    eqs=[]
    for w in set(C):
        f=sp.expand(C[w]-(1 if w==0 else 0))
        if f!=0: eqs.extend(sp.Poly(f,t).all_coeffs())
    if 0 not in C: eqs.append(sp.Integer(-1))
    T1,T2=sp.symbols('T1 T2')
    if corner=='extreme':
        sat=[sp.Symbol(f'p_{degP}_0')*T1-1, sp.Symbol(f'q_{degQ}_0')*T2-1]
    else: # weight-0 dominant: top theta-coefficients at w=0
        sat=[sp.Symbol(f'p_0_{degP//2}')*T1-1, sp.Symbol(f'q_0_{degQ//2}')*T2-1]
    return [sp.expand(e) for e in eqs]+sat, syms+[T1,T2]

def run(d,degP,degQ,corner):
    t0=time.time()
    eqs,vars_=cell_system(d,degP,degQ,corner)
    tb=time.time()-t0
    G=sp.groebner(eqs,*vars_,order='grevlex')
    verdict='EMPTY' if list(G.exprs)==[sp.Integer(1)] else f'NONEMPTY (basis {len(G.exprs)})'
    print(f'S_{d} cell ({degP},{degQ}) corner={corner:8s}: {verdict}   [{len(vars_)} vars, {len(eqs)} eqs, build {tb:.0f}s, total {time.time()-t0:.0f}s]')
    sys.stdout.flush()
    return G

if __name__=='__main__':
    which=sys.argv[1]
    if which=='s4':
        run(4,8,12,'extreme'); run(4,8,12,'w0')
    elif which=='s8':
        run(8,16,24,'extreme'); run(8,16,24,'w0')
    elif which=='s16':
        run(16,32,48,'extreme'); run(16,32,48,'w0')
