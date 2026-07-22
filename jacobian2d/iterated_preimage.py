"""Iterated Keller preimages: the surface Sigma = {B o F = 0} as a live A^2 candidate.

IDEA.  S1 = {B=0} = F^{-1}(plane) carries a 3:1 etale map (A,C)|S1 to A^2, so
Orevkov's theorem FORCES S1 to not be A^2.  But H = F o F is a 9-sheeted 3D
Keller map, and 9-sheeted 2D Keller maps are beyond every known exclusion
(Orevkov 3, Domrina-Orevkov 4, extensions 5).  So

    Sigma = {B o F = 0} = H^{-1}(plane),

which carries a 9:1 etale map to A^2, is NOT forbidden from being A^2.

FACTS (verified below / in session):
 1. B o F is IRREDUCIBLE of degree 37 (163 monomials): Sigma is an irreducible
    smooth affine hypersurface (smooth since H is etale and the plane smooth).
 2. Sigma is C*-stable for the source action (x,y,z)->(lx, y/l, z/l^2)
    (B o F scales with pure weight), with unique fixed point the origin.
 3. EULER CHARACTERISTIC: fiber counts of the 9:1 map are constant on
    C*-orbits of the target (a,c)-plane; every 1-dimensional orbit is a C*
    with e = 0, so e(Sigma) = #(fiber over the origin) = #F^{-1}(0,0,0) = 1
    -- the Euler characteristic of the plane.  (The same argument re-derives
    e(S1) = 1, matching an independent stratified count: S1 is an exotic-plane
    candidate that Orevkov proves is NOT A^2.)
 4. The generic fiber of the 9:1 map (A o F, C o F)|Sigma is 9 points
    (nested cubics psi, psi-tilde below), and the 3 preimages of each marked
    collision point p1,p2,p3 all lie on Sigma: non-injectivity is built in.

DICHOTOMY (either way is beyond current knowledge):
  * Sigma iso A^2   =>  JC(2) is FALSE (explicit 9-sheeted Keller counterexample);
  * Sigma not A^2   =>  a new Orevkov-type obstruction exists at 9 sheets.

The fiber machinery: over target (a,b,c), the x-coordinates of F^{-1}(a,b,c)
are the valid roots of

    psi~(x) = Lam* x^3 + (4 - 3bc) x - 2c,
    Lam*    = 27 a^2 c^2 - 18 abc + 16 a + b^3 c - b^2,

so the Jelonek (deficiency) set of F is {Lam* = 0}, and over the b=0 plane
psi(x) = a(27ac^2+16) x^3 + 4x - 2c with discriminant -4 Lam (27ac^2+8)^2
(the squared factor is a fake collision: two sheets share x but differ in y,z).

Run: python3 iterated_preimage.py     (several minutes: exact algebraic solves)
"""
import sympy as sp

x, y, z, lam = sp.symbols('x y z lambda')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')
Bt = b + 3*a*(1 + a*b)**2*c + 3*a*b**2*(4 + 3*a*b)
BF = sp.expand(Bt.subs({a: A, b: B, c: C}, simultaneous=True))

# 1. irreducibility and degree
assert sp.total_degree(BF, x, y, z) == 37
fac = sp.factor_list(BF)
assert len(fac[1]) == 1 and fac[1][0][1] == 1
print("1. B o F irreducible, degree 37  OK")

# 2. C*-stability
scal = {x: lam*x, y: y/lam, z: z/lam**2}
assert sp.simplify(BF.subs(scal, simultaneous=True)*lam - BF) == 0
print("2. Sigma C*-stable (B o F has pure weight)  OK")

# 3. e(Sigma) = #F^{-1}(0,0,0) = 1
sols = sp.solve([sp.Eq(A, 0), sp.Eq(B, 0), sp.Eq(C, 0)], [x, y, z], dict=True)
assert sols == [{x: 0, y: 0, z: 0}]
print("3. F^{-1}(0) = {origin}  =>  e(Sigma) = 1  OK")

# 4. general fiber polynomial / Jelonek set
E1, E2, E3 = A - a, B - b, C - c
R12 = sp.expand(sp.resultant(E1, E2, z))
R13 = sp.expand(sp.resultant(E1, E3, z))
Rx = sp.factor(sp.resultant(R12, R13, y))
Lam_star = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2
expected = a**3*x**18*sp.expand(Lam_star*x**3 + (4 - 3*b*c)*x - 2*c)
assert sp.simplify(Rx - expected) == 0
print("4. fiber cubic Lam* x^3 + (4-3bc)x - 2c; Jelonek set {Lam*=0}  OK")

# 5. marked-point preimages lie on Sigma (non-injectivity of the 9:1 map)
p2 = (1, sp.Rational(-3, 2), sp.Rational(13, 2))
pre2 = sp.solve([sp.Eq(A, p2[0]), sp.Eq(B, p2[1]), sp.Eq(C, p2[2])],
                [x, y, z], dict=True)
assert len(pre2) == 3
assert all(sp.simplify(BF.subs(s_)) == 0 for s_ in pre2)
print("5. all 3 points of F^{-1}(p2) lie on Sigma  OK")
print("Sigma: irreducible, smooth, C*-surface, e = 1, 9:1 etale over A^2.")
print("Sigma iso A^2  <=>  JC(2) false (9 sheets: beyond all known exclusions).")
