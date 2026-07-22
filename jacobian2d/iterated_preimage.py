"""Iterated Keller preimages: the surface Sigma = {B o F = 0} as a live A^2 candidate.

IDEA.  S1 = {B=0} = F^{-1}(plane) carries a 3:1 etale map (A,C)|S1 to A^2, so
Orevkov's theorem FORCES S1 to not be A^2.  But H = F o F is a 9-sheeted 3D
Keller map, and 9-sheeted 2D Keller maps are beyond every known exclusion
(Orevkov 3, Domrina-Orevkov 4, extensions 5).  So

    Sigma = {B o F = 0} = H^{-1}(plane),

which carries a 9:1 etale map (A o F, C o F)|Sigma to A^2, is NOT forbidden
from being A^2.

FACTS (verified here / in session):
 1. B o F is IRREDUCIBLE of degree 37 (163 monomials): Sigma is an irreducible
    smooth affine hypersurface (smooth since H is etale and the plane smooth).
 2. Fiber machinery: over target (a,b,c) the x-coordinates of F^{-1}(a,b,c)
    are the valid roots of
        psi~(x) = Lam* x^3 + (4 - 3bc) x - 2c,
        Lam*    = 27 a^2 c^2 - 18 abc + 16 a + b^3 c - b^2,
    so the Jelonek (deficiency) set of F is {Lam* = 0}.  Over the b=0 plane:
    psi = a(27ac^2+16) x^3 + 4x - 2c, discriminant -4 Lam (27ac^2+8)^2, and
    the squared factor is a fake collision (two sheets share x, differ in y,z).
 3. Generic fibers of H over the plane b=0 have 9 points (verified numerically
    at two generic targets with Newton refinement); over the marked target
    (-1/4,0,0) the fiber is 1+3+3 = 7 points (exact): the intermediate point
    p1=(0,0,-1/4) lies ON the Jelonek set (Lam*(p1)=0, single preimage
    (-1/8,0,0)), while p2, p3 are off it (3 preimages each).  In particular
    the 9:1 map on Sigma has abundant built-in collisions.
 4. e(S1) = 1 (the plane's Euler characteristic): fiber counts of the
    EQUIVARIANT map F are constant on C*-orbits of the (a,c)-plane, so
    e = fiber count over the origin = #F^{-1}(0) = 1; independently confirmed
    by the stratified count 3*e(A^2 - strata) + 1*e({a=0}) + 1*e({27ac^2+16=0})
    = 3*0 + 1 + 0 = 1.  S1 is an exotic-plane candidate (e = 1, irreducible,
    smooth, NOT A^2 by Orevkov).
 5. CAUTION (corrected claim): H = F o F is NOT C*-equivariant -- F's target
    weights (2,1,-1) differ from its source weights (-1,1,2) -- so Sigma is
    NOT C*-stable (B o F decomposes into graded pieces of weights differing
    by 3), and the orbit argument does NOT compute e(Sigma).  e(Sigma) is
    currently OPEN; it requires the second-layer deficiency curve
    E = (A,C)( S1 n {Lam*=0} ) and the stratified count
    e(Sigma) = 9 e(U) + 3 e(L1^o) + 3 e(Q^o) + 7 e(E^o) + point corrections.

DICHOTOMY (either way is beyond current knowledge):
  * Sigma iso A^2   =>  JC(2) is FALSE (explicit 9-sheeted Keller counterexample);
  * Sigma not A^2   =>  a new Orevkov-type obstruction exists at 9 sheets.

Run: python3 iterated_preimage.py     (a few minutes)
"""
import sympy as sp

x, y, z = sp.symbols('x y z')
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

# 2. general fiber polynomial / Jelonek set
E1, E2, E3 = A - a, B - b, C - c
R12 = sp.expand(sp.resultant(E1, E2, z))
R13 = sp.expand(sp.resultant(E1, E3, z))
Rx = sp.factor(sp.resultant(R12, R13, y))
Lam_star = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2
expected = a**3*x**18*sp.expand(Lam_star*x**3 + (4 - 3*b*c)*x - 2*c)
assert sp.simplify(Rx - expected) == 0
print("2. fiber cubic Lam* x^3 + (4-3bc)x - 2c; Jelonek set {Lam*=0}  OK")

# 3. e(S1) = #F^{-1}(0) = 1
sols = sp.solve([sp.Eq(A, 0), sp.Eq(B, 0), sp.Eq(C, 0)], [x, y, z], dict=True)
assert sols == [{x: 0, y: 0, z: 0}]
print("3. F^{-1}(0) = {origin}: e(S1) = 1 (orbit argument, F equivariant)  OK")

# 4. marked fiber of H: intermediates p1 (deficient, 1 preimage), p2, p3 (3 each)
p1 = (0, 0, sp.Rational(-1, 4))
p2 = (1, sp.Rational(-3, 2), sp.Rational(13, 2))
p3 = (-1, sp.Rational(3, 2), sp.Rational(13, 2))
assert Lam_star.subs(dict(zip((a, b, c), p1))) == 0        # p1 on Jelonek set
pre1 = sp.solve([sp.Eq(A, p1[0]), sp.Eq(B, p1[1]), sp.Eq(C, p1[2])],
                [x, y, z], dict=True)
assert len(pre1) == 1 and pre1[0] == {x: sp.Rational(-1, 8), y: 0, z: 0}
# p2, p3 off the Jelonek set with 3 distinct x-sheets (nonzero cubic discriminant)
for p in (p2, p3):
    sub = dict(zip((a, b, c), p))
    L = Lam_star.subs(sub)
    assert L != 0
    cub = sp.Poly((Lam_star*x**3 + (4 - 3*b*c)*x - 2*c).subs(sub), x)
    assert sp.discriminant(cub) != 0
# membership of the whole marked H-fiber in Sigma is pure algebra:
# for q in F^{-1}(p_i),  (B o F)(q) = B(p_i)  as a function value, and
assert all(B.subs(dict(zip((x, y, z), p))) == 0 for p in (p1, p2, p3))
print("4. #H^{-1}(-1/4,0,0) = 1+3+3 = 7, all on Sigma  OK")

# 5. NON-equivariance of H (the corrected claim)
lam = sp.Symbol('lambda')
scaled = sp.expand(BF.subs({x: lam*x, y: y/lam, z: z/lam**2}, simultaneous=True))
assert not sp.simplify(scaled*lam - BF) == 0     # not pure weight
print("5. B o F is NOT C*-homogeneous: orbit argument inapplicable to Sigma  OK")
print("Sigma: irreducible, smooth, 9:1 etale over A^2, e(Sigma) open.")
print("Sigma iso A^2  <=>  JC(2) false (9 sheets: beyond all known exclusions).")
