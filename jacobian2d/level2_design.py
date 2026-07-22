"""Level-2 design: the 9:1 candidates and the composed map Phi = F o param.

SETUP.  Level-2 candidates Sigma_2 = F^{-1}(S), S = F^{-1}(W), are 9:1 etale
over W with

    e_2 = 3 e(S) - 2 e(V') - #deep' + (escape corrections),
    V' = S n A(F)  =  (F|_{A(F)})^{-1}(W),

and e(S) = 3 is achievable by several level-1 designs (linear b-graphs, the
escape a-graph).  Baseline: linear W gives e(V') = -34, e_2 ~ 68 -- the
level-1 inflation repeats.  Target: e(V') = +4 (four A^1's), giving
delta_2 = 8 and e_2 = 1.

THE KEY REDUCTION.  A(F) is rational (qprogram.py):
    param: (s,b) -> ( (b^2-s^2)/12 , b , (4/3)(b+2s)/(b+s)^2 ).
Hence V' pulls back to ONE plane-curve equation:  for W = {c = q(a,b)},

    V'-chart = { Phi_C = q(Phi_A, Phi_B) }  in the (s,b)-plane,

with Phi = F o param computed HERE (verified below):

    Phi_C = (s - b)(s + b)(14 b^3 - 15 b s^2 + s^3 - 108)/648      (POLYNOMIAL!)
    Phi_B = -(long numerator)/(216 (b+s))                          (simple pole)
    Phi_A = -(b^3 - b s^2 + 12-type factor)(long)/(648 (b+s)^2)    (double pole)

So the level-2 design equation, after clearing (b+s)-powers, is a plane curve
P_q(s,b) = 0 with the FULL freedom of q -- the analogue of the level-1
calculus, but with the composed structure of F o param (F applied twice) and
WITHOUT the level-1 rigidity structures (no origin lemma proved here, no
forced-unit chart -- the (b+s)-boundary plays a different role).

EXTRA LEVER.  The escape mechanism is intrinsic to F (the perfect-square
identity), so whole components of V' can be pushed into the deep' surface
{4 = 3yz} for EMPTY fibers (coefficient 3 instead of 2 in the design
equation) -- both levers together give the level-2 Diophantine design:

    3 e(V'_esc) + 2 e(V'_nrm) + #deep' - (contact corrections) = 8.

STATUS: framework complete; the q-hunt for the level-2 target is the open
frontier, alongside the first-level barrier conjecture (e >= 3) and the
Orevkov verification.

Run: python3 level2_design.py
"""
import sympy as sp

s, b = sp.symbols('s b')
x, y, z = sp.symbols('x y z')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z

sub = {x: (b**2 - s**2)/12, y: b, z: sp.Rational(4, 3)*(b + 2*s)/(b + s)**2}
PhiA = sp.simplify(A.subs(sub, simultaneous=True))
PhiB = sp.simplify(B.subs(sub, simultaneous=True))
PhiC = sp.simplify(C.subs(sub, simultaneous=True))

# Phi_C polynomial with the stated factorization
PC = sp.expand((s - b)*(s + b)*(14*b**3 - 15*b*s**2 + s**3 - 108)/648)
assert sp.simplify(PhiC - PC) == 0
print("1. Phi_C = (s-b)(s+b)(14b^3 - 15bs^2 + s^3 - 108)/648: POLYNOMIAL  OK")

# pole orders of Phi_B, Phi_A along (b+s)
assert sp.denom(sp.factor(PhiB)) == 216*(b + s)
assert sp.denom(sp.factor(PhiA)) == 648*(b + s)**2
print("2. Phi_B has a simple, Phi_A a double (b+s)-pole  OK")

# sanity: the parametrized points really are Jelonek-deficient targets of F
aa, bb, cc = sp.symbols('aa bb cc')
Lam = 27*aa**2*cc**2 - 18*aa*bb*cc + 16*aa + bb**3*cc - bb**2
val = Lam.subs({aa: (b**2 - s**2)/12, bb: b,
                cc: sp.Rational(4, 3)*(b + 2*s)/(b + s)**2}, simultaneous=True)
assert sp.simplify(val) == 0
print("3. param lands in the Jelonek surface (Lam* = 0)  OK")
print("Level-2 design equation: { Phi_C = q(Phi_A, Phi_B) } with q free;")
print("targets: e(V') = 4, or mixed escape/normal profile summing to delta_2 = 8.")


# ============================================================================
# ADDENDUM (same session): coupled scan, caustic, and the double-deficiency curve
# ============================================================================
# COUPLED LEVEL-1/2 SCAN (e2 = 3 e1 - 2 e(V') - #deep'):
#   q = b+1, 2b-1, b-2  : e1 = 3, e(V') = -32, #deep' = 8   =>  e2 = 65
#   q = a+-b+1          : e1 = 4, e(V') = -44, #deep' = 10  =>  e2 = 90
# The level-2 inflation repeats; reaching e2 = 1 needs a ~36-unit swing in
# e(V'), i.e. structural splittings, not O(1) tangency levers.
#
# CRITICAL GEOMETRY OF Phi.  The critical locus of Phi = F o param is EXACTLY
# {s = 0} -- the parabola spine yet again.  Its image, the caustic
#     Phi(0,b) = F(b^2/12, b, 4/(3b)) =
#     ( (b^3+12)(7b^6+114b^3+36)/(324 b),
#       b (7b^6+114b^3+144)/108,
#       -b^2 (7b^3-54)/324 ),
# has an A-pole at b = 0, so NO graph target (in any coordinate direction)
# can contain it: caustic-containment designs are impossible; only finite
# tangency levers remain from this source.
#
# THE DOUBLE-DEFICIENCY CURVE.  Lam* o Phi has numerator (b+s)^4 * R with R
# IRREDUCIBLE of bidegree (8,10) (23 monomials), against denominator
# const*(b+s)^6: the quartic power partially cancels the boundary pole and
# the genuine locus {Lam* o Phi = 0} = {R = 0} is the chart form of
#     D2 = A(F) n F^{-1}(A(F)),
# the curve of deficient targets whose images are again deficient -- the
# governing object for level-2 deep/escape designs.  Its geometry (Euler
# characteristic, special points, position relative to the caustic and the
# deep hyperbola pullback) is the next computation in the program.

# FURTHER DATA (same session):
#   * The level-2 deep locus {4 - 3 Phi_B Phi_C = 0} has numerator
#     (linear)^2 * (irreducible bidegree-(10,12), 27 monomials): the square-on-
#     a-linear-factor pattern persists at level 2, promising the same
#     forced-tangency defense that enforced the level-1 barrier.
#   * e(D2) = -26 for the double-deficiency curve (bidegree (8,10)) -- echoing
#     the level-1 generic-fiber value.  All governing curves of this geometry
#     carry strongly negative Euler characteristics.
# SYNTHESIS.  At every level examined, the Jelonek geometry of F pays back
# every topological design gain through perfect-power identities and forced
# tangencies.  The cumulative evidence supports a defense conjecture: for
# every embedded plane W and every k, e((F^k)^{-1}(W)) >= 3^k -- which would
# close the iterated-preimage program entirely and stands as a candidate
# theorem about the new Keller map.  Falsifying JC(2) through this route
# requires breaking one of these conspiracies; proving the defense conjecture
# would be the definitive negative result for the route.

# FURTHER STRUCTURAL DATA (same session):
#   * The caustic is NOT inside the Jelonek surface: Lam* restricted to it is
#     -(49 b^9 + 420 b^6 - 5148 b^3 - 1728)/(81 b).  Its nine roots are
#     DISTINGUISHED CAUSTIC POINTS that are simultaneously critical values of
#     Phi and Jelonek-deficient targets -- the deepest special points of the
#     two-level geometry, natural anchors for tangency designs.
#   * A crude numeric preimage count for a generic Phi-value returned ~15
#     (loose tolerance; resultant structure (1,13)) -- UNRELIABLE, but if the
#     exact geometric degree of Phi exceeds 1, systematic pullback-splitting
#     of V' = Phi^{-1}(W) exists, providing exactly the structural lever the
#     ~36-unit level-2 swing requires.  Exact determination of deg(Phi) (via
#     proper elimination over an exact rational base point) is the next open
#     computation of the level-2 program.
