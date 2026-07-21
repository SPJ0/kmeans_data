import sympy as sp, pickle, time, sys
t0=time.time()
cons, vars_used = pickle.load(open('s16_constraints_ring.pkl','rb'))
print(f'loaded {len(cons)} constraints [{time.time()-t0:.0f}s]', flush=True)
def size(c):
    return len(c.args) if c.is_Add else 1
sized = sorted(((size(c), i) for i, c in enumerate(cons)))
print('constraint sizes (smallest 20):', [s for s, _ in sized[:20]], flush=True)
print('constraint sizes (largest 5):', [s for s, _ in sized[-5:]], flush=True)
vs = [sp.Symbol(v) for v in vars_used]
for k in (10, 20, 35, 60, 90, 125):
    sub = [cons[i] for _, i in sized[:k]]
    t1 = time.time()
    try:
        G = sp.groebner(sub, *vs, order='grevlex')
        empty = (list(G.exprs) == [sp.Integer(1)])
        print(f'k={k:3d}: {"EMPTY -- CELL CLOSED" if empty else f"consistent so far (basis {len(G.exprs)})"} [{time.time()-t1:.0f}s]', flush=True)
        if empty: sys.exit(0)
        if k >= 35 and len(G.exprs) < 40:
            for g in list(G.exprs)[:12]: print('   basis elt:', sp.sstr(g)[:140], flush=True)
    except Exception as e:
        print(f'k={k}: failed {type(e).__name__}: {str(e)[:200]}', flush=True); break
print('exhausted without EMPTY verdict', flush=True)
