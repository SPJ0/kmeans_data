"""e(Sigma4) = 103 != 1  =>  generation 4 is NOT A^2 (fifth kill mechanism).

THE A-FIBRATION EULER MACHINERY (reusable for any candidate surface
Sigma_P = F^{-1}(S_P)):  fiber Sigma_P by the function A (= x o F).  Its fiber
over nu is F^{-1}(gamma_nu), gamma_nu = {x=nu} n S_P -- only ONE level of F is
involved, so everything reduces to one-variable analysis in nu:

    gamma_nu = graph of z = (1-N0)/D over y,  punctures at D-roots (p of them),
    deficiency points where Lam* vanishes on the graph (m of them, from the
    numerator Lnum of bidegree (7,10)),
    n = 1 preimage at a deficiency point (the cubic psi~ = Lam* x^3 + (4-3bc)x
    - 2c has NO quadratic term, so it degenerates straight to LINEAR -- this
    also retro-explains the gen-1 observation #H^{-1} = 7 = 3+3+1),
    n = 0 at "deep" points (Lam* = 0 AND 4-3bc = 0),

    e(fiber_nu) = 3(1 - p - m) + (m - #deep).

Generic profile: p=3, m=10  =>  e_gen = -26.  Exact assembly over the nu-line:

    e(Sigma4) = e(fiber_0) + e_gen*(1 - 1 - #special) + sum_special e(fiber),

with the special nu enumerated EXACTLY as roots of irreducible factors of
  disc_y(Lnum), lc_y(Lnum), res_y(Lnum, D), res_y(D, 1-N0), res_y(Lnum, deep):
after stripping the x-power artifacts these are ONE cubic, ONE degree-9, and
ONE degree-39 irreducible factor (with meaningful coincidences: the cubic
appears in all four special polynomials).  By Galois conjugacy the fiber
profile is constant on the roots of each irreducible factor, so ONE
high-precision evaluation per factor suffices (all coefficients handled as
exact rationals -> mpmath; double-precision casts provably corrupt the
degree-39 factor):

    nu = 0        : p=0, m=4            e = -5
    cubic  (x3)   : p=2, m=8,  deep=0   e = -19   contribution 3*(+7)  = 21
      (an artifact double root of Lnum absorbs two deficiency points into a
       filled pole: the pole of the graph cancels against 1-N0, and the two
       colliding deficiency points cease to be deficient in the limit)
    deg-9  (x9)   : p=3, m=9,  deep=1   e = -25   contribution 9*(+1)  = 9
      (the collision happens exactly AT a deep point)
    deg-39 (x39)  : p=3, m=9,  deep=0   e = -24   contribution 39*(+2) = 78
      (simple collisions; verified at two independent roots: colliding pair
       at gap ~1e-40, next gap ~1e-4)

    e(Sigma4) = -26*(-51) + [3(-19) + 9(-25) + 39(-24) + (-5)] = 1326 - 1223
              = 103.

Since e(A^2) = 1, Sigma4 is NOT the affine plane.  DESIGN EQUATION for any
future candidate: e = 1 requires the deficiency corrections to sum to exactly
d - 1 (= 8 for 9-sheeted candidates); here they summed to -94.  The etale
covers ACCUMULATE topology; a viable candidate needs engineered massive
cancellation in its Jelonek geometry.

Run: python3 euler_sigma4.py   (recomputes the profile table, ~2 min)
"""
import sympy as sp
import mpmath as mp

mp.mp.dps = 60
x, y, z = sp.symbols('x y z')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
K3 = sp.expand(A + B + C)
D = sp.expand(sp.diff(K3, z))
N0 = sp.expand(K3 - D*z)
N1 = sp.expand(1 - N0)
a, b, c = sp.symbols('a b c')
Lam = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2
zg = (1 - N0)/D
Lnum = sp.expand(sp.numer(sp.together(Lam.subs({a: x, b: y, c: zg},
                                               simultaneous=True))))
deepnum = sp.expand(sp.numer(sp.together(4 - 3*y*zg)))

specials = {
    'disc_L': sp.discriminant(sp.Poly(Lnum, y)),
    'res_LD': sp.resultant(Lnum, D, y),
    'res_DN': sp.resultant(D, N1, y),
    'res_Ldeep': sp.resultant(Lnum, deepnum, y),
}
factors = {}
for k, P in specials.items():
    for f, m in sp.factor_list(P)[1]:
        if sp.degree(f, x) == 0 or sp.expand(f) == x:
            continue
        fp = sp.Poly(f, x).monic()
        factors[sp.srepr(fp.as_expr())] = fp

def to_mp(q):
    q = sp.Rational(q)
    return mp.mpf(int(q.p))/mp.mpf(int(q.q))

def ycoeffs_at(P, xv):
    out = []
    for co in sp.Poly(P, y).all_coeffs():
        val = mp.mpc(0)
        for cc in sp.Poly(co, x).all_coeffs():
            val = val*xv + to_mp(cc)
        out.append(val)
    return out

def eval_bi(P, xv, yv):
    val = mp.mpc(0)
    for co in ycoeffs_at(P, xv):
        val = val*yv + co
    return val

def profile(xv):
    dro = mp.polyroots(ycoeffs_at(D, xv), maxsteps=400, extraprec=200)
    lro = mp.polyroots(ycoeffs_at(Lnum, xv), maxsteps=400, extraprec=200)
    p = sum(1 for r in dro if abs(eval_bi(N1, xv, r)) > mp.mpf(10)**-20)
    dist = []
    for r in lro:
        if any(abs(r - q) < mp.mpf(10)**-18 for q in dist):
            continue
        if any(abs(r - dr) < mp.mpf(10)**-18 for dr in dro):
            continue
        dist.append(r)
    deep = sum(1 for r in dist
               if abs(eval_bi(deepnum, xv, r)) < mp.mpf(10)**-15)
    return p, len(dist), deep

total = -5                                     # e(fiber over nu = 0)
table = {3: (2, 8, 0, -19), 9: (3, 9, 1, -25), 39: (3, 9, 0, -24)}
for key, fp in factors.items():
    deg = fp.degree()
    roots = mp.polyroots([to_mp(v) for v in fp.all_coeffs()],
                         maxsteps=500, extraprec=300)
    r0 = max(roots, key=lambda r: min([abs(r - s) for s in roots if s != r]
                                      or [mp.mpf(1)]))
    p, m, deep = profile(r0)
    e_f = 3*(1 - p - m) + (m - deep)
    assert (p, m, deep, e_f) == table[deg], (deg, p, m, deep, e_f)
    total += deg*(e_f + 26)
    print(f"factor deg {deg}: p={p} m={m} deep={deep} e={e_f}")
assert total == 103
print("e(Sigma4) =", total, " != 1  =>  Sigma4 is NOT A^2.")
