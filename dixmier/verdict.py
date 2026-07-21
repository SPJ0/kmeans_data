import sympy as sp, pickle, time, sys
cons, vars_used = pickle.load(open('s16_constraints_ring.pkl','rb'))
vs=[sp.Symbol(v) for v in vars_used]
print(f'{len(cons)} constraints, {len(vs)} vars; degrees:', sorted({sp.total_degree(c) for c in cons}))
mode=sys.argv[1] if len(sys.argv)>1 else 'modp'
t0=time.time()
if mode=='modp':
    for p in (2147483647, 2147483629):
        G=sp.groebner(cons,*vs,order='grevlex',modulus=p)
        v='EMPTY' if list(G.exprs)==[sp.Integer(1)] else f'NONEMPTY (basis {len(G.exprs)})'
        print(f'mod {p}: {v} [{time.time()-t0:.0f}s]',flush=True)
        if 'NONEMPTY' in v:
            for g in list(G.exprs)[:6]: print('  ',g)
            break
else:
    G=sp.groebner(cons,*vs,order='grevlex')
    print('exact:','EMPTY' if list(G.exprs)==[sp.Integer(1)] else f'NONEMPTY (basis {len(G.exprs)})', f'[{time.time()-t0:.0f}s]',flush=True)
