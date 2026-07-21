import sympy as sp, itertools
from weyl import t, mul, comm, add, clean

def partner_solve(P, W, D, verbose=False):
    """Solve [Q,P]=1 for Q in window |w|<=W, deg_theta <= D. Returns (particular, kernel_dim) or None."""
    cs = {}
    Q = {}
    for w in range(-W, W+1):
        for j in range(D+1):
            c = sp.Symbol(f'c_{w}_{j}')
            cs[(w,j)] = c
            Q[w] = sp.expand(Q.get(w,0) + c*t**j)
    C = comm(Q, P)
    eqs = []
    for w, f in C.items():
        target = 1 if w == 0 else 0
        p = sp.Poly(sp.expand(f - target), t)
        eqs.extend(p.all_coeffs())
    if 0 not in C: eqs.append(sp.Integer(-1))  # weight-0 comp must exist and equal 1
    unk = list(cs.values())
    sol = sp.linsolve([sp.expand(e) for e in eqs], unk)
    if not sol: return None
    solv = list(sol)[0]
    free = sorted(set().union(*[s.free_symbols for s in solv]) & set(unk), key=str)
    part = {u: v.subs({f2: 0 for f2 in free}) for u, v in zip(unk, solv)}
    Qp = clean({w: sp.expand(sum(part[cs[(w,j)]]*t**j for j in range(D+1))) for w in range(-W,W+1)})
    return Qp, len(free)

print('== single-weight theorem, mechanical check (P = g(theta) d^k) ==')
for k in (1,2,3):
    for g in (sp.Integer(1), t, t**2+1, t*(t-1)):
        P = {-k: g}
        r = partner_solve(P, W=k+3, D=6)
        tag = f'k={k}, g={g}'
        print(f'  {tag:24s} partner exists: {r is not None}' + (f'  (Q = {r[0]}, ker dim {r[1]})' if r else ''))

print('== two-weight probes ==')
probes = {
 'd + x^2 (tame)':        {-1: sp.Integer(1), 2: sp.Integer(1)},
 'd + x^3 (tame)':        {-1: sp.Integer(1), 3: sp.Integer(1)},
 '(1+t)d + x^2':          {-1: 1+t, 2: sp.Integer(1)},
 't d^2 + x':             {-2: t, 1: sp.Integer(1)},
 't d^2 + x^3':           {-2: t, 3: sp.Integer(1)},
 '(t^2+1)d^3 + x^2':      {-3: t**2+1, 2: sp.Integer(1)},
 'd^2 + x^3 (deg 2,3)':   {-2: sp.Integer(1), 3: sp.Integer(1)},
}
for name, P in probes.items():
    r = partner_solve(P, W=6, D=6)
    if r: print(f'  {name:24s} PARTNER FOUND, kernel dim {r[1]}: Q =', r[0])
    else: print(f'  {name:24s} no partner in box (W=6, D=6)')
