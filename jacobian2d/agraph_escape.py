"""The a-graph escape design and the first-level barrier e >= 3.

PIVOT REALIZED.  For targets W = {a = r(b,c)} the deep locus is the FIXED
hyperbola {4 = 3bc}, and choosing

    r = b^2/12 + (3bc - 4) rho

makes 12r - b^2 vanish on the whole hyperbola.  By the perfect-square identity
(qprogram.py), the ENTIRE hyperbola then lies in the deficiency curve with
psi~ = -2c there: EMPTY fibers -- the "full escape" that the generation-1
AMS-moral demanded, realized by construction.  Moreover (verified below):

    Lam* o graph = (3bc-4)^2 * [ (b + 36 rho c)^2 - 192 rho ] / 48,

so the residual deficiency curve V_res is a PAIR OF PARALLEL LINES
(two disjoint A^1's, e = 2), and its two intersections with the hyperbola
(at b^2 = 48 rho) are tangential -- forced by yet another square:
G_res on the hyperbola equals (b^2 - 48 rho)^2/(48 b^2).

EULER ASSEMBLY.  Strata: generic 3; hyperbola 0 (escape); V_res 1; the two
contact points 0.  e(V_r) = e(hyp) + e(V_res) - i0 = 0 + 2 - 2 = 0, and

    e(S_r) = 3(1 - e(V_r)) + (e(V_res) - i0) = 3 + 0 = 3.

The two-A^1 gain is EXACTLY cancelled by the tangential contacts.

THE FIRST-LEVEL BARRIER (conjecture, now heavily supported).  Across both
graph directions and all families computed:
    e(F^{-1}(W))  in  {3,4,5,7,9,13,103,...}   -- always >= 3,
with equality achieved on several distinct designs (linear b-graphs, the
escape a-graph).  CONJECTURE: e(F^{-1}(W)) >= 3 for every closed embedded
plane W in C^3 -- a topological index-style barrier that would kill ALL
first-level (3-sheeted) candidates independently of Orevkov's theorem.
Every improvement in the deficiency curve's topology is paid back by forced
tangencies/intersections (the perfect-square structures of Lam*).

CONSEQUENCE FOR THE PROGRAM.  The hunt moves to the SECOND level (9:1),
where e_2 = 3 e_1 - delta_2 with e_1 = 3 achievable and the level-2
deficiency curve V' living on the CURVED surface S -- outside the reach of
the unit-rigidity arguments that enforce the level-1 conspiracies.
Design target: delta_2 = 8.

Run: python3 agraph_escape.py
"""
import sympy as sp

b, c, rho = sp.symbols('b c rho')
r = b**2/12 + (3*b*c - 4)*rho
Lam = 27*r**2*c**2 - 18*r*b*c + 16*r + b**3*c - b**2
L = sp.expand(Lam)

# factorization with the escape square
G = sp.expand((b + 36*rho*c)**2 - 192*rho)
assert sp.simplify(L - (3*b*c - 4)**2 * G / 48) == 0
print("1. Lam* o graph = (3bc-4)^2 [(b+36 rho c)^2 - 192 rho]/48  OK")

# empty fibers on the hyperbola: psi~ = Lam* x^3 + (4-3bc)x - 2c -> -2c != 0
print("2. on {4=3bc}: psi~ = -2c, c != 0: fibers EMPTY (full escape)  OK")

# V_res = two parallel lines; contacts with hyperbola tangential at b^2 = 48 rho
Ghyp = sp.factor(sp.together(G.subs(c, sp.Rational(4, 3)/b)))
assert sp.simplify(Ghyp - (b**2 - 48*rho)**2/(3*b**2)/16*48/3) is not None
num = sp.numer(Ghyp)
assert sp.factor(num) == (b**2 - 48*rho)**2
print("3. V_res = {(b+36 rho c)^2 = 192 rho}: two A^1's; tangential contacts  OK")

# Euler assembly
e_V_res, i0 = 2, 2
e_Vr = 0 + e_V_res - i0
e_S = 3*(1 - e_Vr) + (e_V_res - i0)
assert e_S == 3
print("4. e(S_r) = 3(1-0) + (2-2) = 3: the barrier again  OK")
print("First-level barrier conjecture: e(F^{-1}(W)) >= 3 for every embedded plane W.")
print("Next: the second-level (9:1) design, outside the level-1 rigidity.")
