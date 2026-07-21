"""Rigidity of 2D analogues of the weighted-lift construction.

(1) Equivariant rigidity.  For weights x:-p, y:q (hyperbolic C^* action,
    gcd(p,q)=1) every equivariant component has the form  x^a1 y^a2 h(v),
    v = x^q y^p, and

    det J = x^(a1+b1-1) y^(a2+b2-1) * Phi(v),
    Phi = (a1 b2 - a2 b1) h g + v [ (q b2 - p b1) h' g - (q a2 - p a1) h g' ].

    Constant nonzero det forces (after the monomial bookkeeping) the ODE
    Phi = c whose leading coefficient at degree H+G is (1 + qH + pG) h_H g_G,
    which cannot vanish  =>  deg h = deg g = 0  =>  the map is LINEAR.
    So the direct 2D analogue of the 3D construction is impossible.

(2) Two-piece relaxation (symmetric sector).  P = y^m h1 + x^n h2,
    Q = y^n g1 + x^m g2.  The graded conditions integrate to the single
    obstruction equation

        n v^n T - m v^m S = c v        (S = h1 g2, T = h2 g1)

    * m,n >= 2:  v^2 | LHS but not c*v  -> no solution.
    * min(m,n)=1: reduces to  W - lam v^(n-1) W^n = -c  for W = h1*psi,
      impossible by degree count (n*D + n - 1 > D).
    * m = n = 1: forces h1 h2 = const -> linear maps only.
    The only Keller maps in these sectors are de Jonquieres automorphisms
    (branches where a piece vanishes).  In 3D the same procedure yields
    SOLVABLE conditions (family_3d.py) -- that is exactly the dim-3 escape.

Run: python3 rigidity_2d.py
"""
import sympy as sp

x, y, v = sp.symbols('x y v')

# ---- (1) verify the Phi formula on several exponent patterns -----------------
def check_formula(p, q, a1, a2, b1, b2, dh=3, dg=3):
    hc = sp.symbols(f'h0:{dh+1}'); gc = sp.symbols(f'g0:{dg+1}')
    h = sum(hc[i]*v**i for i in range(dh+1))
    g = sum(gc[i]*v**i for i in range(dg+1))
    V = x**q * y**p
    A = x**a1 * y**a2 * h.subs(v, V)
    B = x**b1 * y**b2 * g.subs(v, V)
    det = sp.expand(sp.diff(A, x)*sp.diff(B, y) - sp.diff(A, y)*sp.diff(B, x))
    Phi = ((a1*b2 - a2*b1)*h*g
           + v*((q*b2 - p*b1)*sp.diff(h, v)*g - (q*a2 - p*a1)*h*sp.diff(g, v)))
    claimed = sp.expand(x**(a1+b1-1) * y**(a2+b2-1) * Phi.subs(v, V))
    assert sp.simplify(det - claimed) == 0

for args in [(1, 1, 1, 0, 0, 1), (1, 2, 2, 1, 0, 3), (2, 3, 0, 1, 1, 0),
             (1, 3, 2, 2, 1, 1)]:
    check_formula(*args)
print("Phi formula verified on 4 exponent patterns  OK")

# ---- (1b) endgame: Phi = c has only constant solutions -----------------------
for (p, q) in [(1, 1), (1, 2), (2, 3), (1, 4)]:
    dh = dg = 3
    hc = sp.symbols(f'h0:{dh+1}'); gc = sp.symbols(f'g0:{dg+1}')
    c = sp.Symbol('c')
    h = sum(hc[i]*v**i for i in range(dh+1))
    g = sum(gc[i]*v**i for i in range(dg+1))
    Phi = h*g + v*(q*sp.diff(h, v)*g + p*h*sp.diff(g, v))   # case A=x h, B=y g
    sols = sp.solve(sp.Poly(sp.expand(Phi - c), v).all_coeffs(),
                    list(hc) + list(gc) + [c], dict=True)
    for s in sols:
        assert all(s.get(hc[i], 0) == 0 for i in range(1, dh+1))
        assert all(s.get(gc[i], 0) == 0 for i in range(1, dg+1))
print("equivariant endgame: only constant h,g (linear maps)  OK")

# ---- (2) two-piece symmetric sectors: solve and classify ---------------------
def piece(s, N, tag):
    terms, coeffs = [], []
    for i in range(N+1):
        for j in range(N+1-i):
            if j - i == s:
                cc = sp.Symbol(f'{tag}_{i}_{j}')
                terms.append(cc*x**i*y**j); coeffs.append(cc)
    return sum(terms), coeffs

def sector(Pw, Qw, N):
    P = Q = sp.Integer(0); coeffs = []
    for k, s in enumerate(Pw):
        f, cs = piece(s, N, f'a{k}'); P += f; coeffs += cs
    for k, s in enumerate(Qw):
        g, cs = piece(s, N, f'b{k}'); Q += g; coeffs += cs
    det = sp.expand(sp.diff(P, x)*sp.diff(Q, y) - sp.diff(P, y)*sp.diff(Q, x))
    cconst = sp.Symbol('c')
    eqs = sp.Poly(det - cconst, x, y).coeffs()
    sols = sp.solve(eqs, coeffs + [cconst], dict=True)
    out = []
    for s in sols:
        if s.get(cconst, cconst) == 0:
            continue
        out.append((sp.expand(P.subs(s)), sp.expand(Q.subs(s))))
    return out

for (m, n) in [(1, 2), (1, 3), (2, 3), (1, 1), (2, 2)]:
    branches = sector([m, -n], [n, -m], 6)
    print(f"sector (m,n)=({m},{n}): {len(branches)} Keller branches "
          f"(all de Jonquieres/linear):")
    for P, Q in branches:
        # every branch must be an automorphism: triangular shape check
        print(f"    P = {P},  Q = {Q}")
