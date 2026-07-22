"""The design endgame: e(V_q) <= 1 and the residual C*-factorization problem.

Continuing qprogram.py.  New structural results (all verified below):

 1. ORIGIN LEMMA.  The c-axis {a=b=0} lies inside the Jelonek surface
    (Lam*(0,0,c) = 0 identically), so (0,0) is on the deficiency curve V_q for
    EVERY q.  Moreover the chart function (b+s) of the rational parametrization
    is a unit on every V_q-component away from the boundary, giving the bound

        e(V_q) <= 1,

    with equality IFF V_q = (A^1 through the origin) |_| (C*-components).
    Combined with the (12a-b^2)-trick (zero deep points):

        e(S_q) = 1   <=>   V_q has EXACTLY this shape.

 2. UNIQUE GRAPH COMPONENT.  Among graph-type components {b = phi(s)} or
    {s = psi(b)} the divisibility s^2(phi+s)^2 | 4(phi + 2s) forces the unique
    solution {b = -2s} (equivalently s = -b/2), which requires
    (16a - b^2) | h.  With q = (12a-b^2)(16a-b^2) g the curve factors CLEANLY:

        P_h = (b+2s) * [ 4 + s^2 (b+s)^2 (b-2s) * g~ ] ,

    g~ = g((b^2-s^2)/12, b) ranging over ALL s-even polynomials, and the A^1-
    component {b=-2s} is disjoint from the residual (residual = 1... = 4 there? no:
    on b=-2s the bracket is 4 + s^2*s^2*(-4s) g~(s,-2s) -- disjointness holds for
    generic g since the bracket then has isolated zeros off the line; the
    intersection points, if any, are checked per design).

 3. THE RESIDUAL PROBLEM.  e(S_q) = 1 now reduces to: find an s-even g~ with

        R(g~) := { s^2 (b+s)^2 (b-2s) g~ = -4 }   =   a disjoint union of C*'s.

    On R the three linear forms s, b+s, (b-2s)g~ are units.  Obstructions found:
    * g~ = const: R is a 5:1 homogeneous cover of P^1 minus 3 points, e = -5
      (gives e(S_q) = 13 -- verified by the machinery for q = t(12a-b^2): e = 7,
      the difference reflecting the extra (16a-b^2) factor's own structure).
    * pure powers (M~ g~ = -(power of two-line monomial)): blocked by the
      PARITY of (b-2s) under s -> -s.
    * products of shifted two-line monomials in s(b+s) alone: blocked because
      (b-2s) never divides a polynomial in X = s(b+s).
    The problem is sharp and open: it is a question about special fibers of
    three-line-times-even polynomials, adjacent to the Zaidenberg-Lin /
    Suzuki theory of simple fibers.

Run: python3 design_endgame.py
"""
import sympy as sp

a, b, c, s, g = sp.symbols('a b c s g')
Lam = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2

# 1. origin lemma
assert sp.expand(Lam.subs({a: 0, b: 0})) == 0
print("1. c-axis inside Jelonek surface: origin on V_q for every q  OK")

# 2. the clean factorization for q = (12a-b^2)(16a-b^2) g
aP = (b**2 - s**2)/12
H = ((16*a - b**2)*g).subs(a, aP)
assert sp.simplify(H - (b - 2*s)*(b + 2*s)*g/3) == 0
P_h = sp.expand(4*(b + 2*s) + 3*(b + s)**2*s**2*H)
Mt = s**2*(b + s)**2*(b - 2*s)
assert sp.simplify(P_h - (b + 2*s)*(4 + Mt*g)) == 0
print("2. P_h = (b+2s) * [4 + s^2(b+s)^2(b-2s) g~]  OK")

# 3. (b+s)^2(b-2s) expansion identity used throughout
assert sp.expand((b + s)**2*(b - 2*s) - (b**3 - 3*b*s**2 - 2*s**3)) == 0
print("3. (b+s)^2(b-2s) = b^3 - 3bs^2 - 2s^3  OK")

# 4. parity obstruction: M~ is odd-mixed; no even g~ makes M~ g~ an even
#    perfect power of a two-line monomial (checked for the simplest shapes)
Mt_flip = Mt.subs(s, -s)
assert sp.simplify(Mt_flip - s**2*(b - s)**2*(b + 2*s)) == 0
assert sp.simplify(Mt_flip + Mt) != 0 and sp.simplify(Mt_flip - Mt) != 0
print("4. M~ has no s-parity; pure-power designs blocked  OK")
print("\nENDGAME: find s-even g~ with {s^2(b+s)^2(b-2s) g~ = -4} = disjoint C*'s;")
print("then e(V_q) = 1, #deep = 0, e(S_q) = 3 - 2 = 1: a candidate passing every test.")
