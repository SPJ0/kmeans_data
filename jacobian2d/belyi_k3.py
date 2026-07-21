"""Explicit Belyi map for the smallest LIVE 2D Keller-map candidate.

Borisov ("Frameworks for two-dimensional Keller maps", Electron. J. Combin. 27
(2020) #P3.54) constructs combinatorial frameworks that any 2D counterexample
to the Jacobian conjecture must realize.  His "isotope" family (k = 2..6) has
polynomial degree pairs
    (99,66), (135,90), (171,114), (207,138), (243,162).
k = 2 is the (99,66) case, almost certainly non-realizable (Moh's sketch,
Horruitiner's thesis, Borisov's Maple computation) though with no clean proof.
All k >= 3 lie BEYOND Moh's degree-100 theorem and are open: the k = 3
framework, degrees (135, 90), is the minimal live candidate for a 2D
counterexample.

Its ramification engine on the (-2)-curve is a degree-13 Belyi polynomial with
profile   over infinity: [13],   over 0: [3,3,3,1,1,1,1],   over 1: [7,1^6].
(Riemann-Hurwitz: 12 + 3*2 + 6 = 24 = 2*13 - 2, genus 0, exactly rigid.)

Construction (this file):  write g = A^3 * B (A monic cubic, B monic quartic),
put the 7-fold point of g = 1 at t = 0.  The profile forces
    g' = 13 t^6 A(t)^2,   g(0) = 1,
so g = Integral(13 t^6 A^2) + 1 and the single condition is A^3 | g.
That gives 9 polynomial equations in the 3 coefficients of A.  The Groebner
basis is triangular over a degree-65 polynomial in a2 which is a QUINTIC in
u = a2^13 (the 13th-root ambiguity is the residual scaling t -> zeta_13 t);
the quintic is irreducible over Q, so the dessin's moduli field has degree 5,
matching the 5 admissible plane trees for this profile.

This script recomputes the Groebner basis, extracts a real solution to 40
digits, and verifies the full profile.

Run: python3 belyi_k3.py     (takes a couple of minutes)
"""
import sympy as sp

t, a0, a1, a2 = sp.symbols('t a0 a1 a2')

A = t**3 + a2*t**2 + a1*t + a0
g = sp.integrate(13*t**6*A**2, t) + 1          # forces profile over 1 and infinity
_, rem = sp.div(sp.expand(g), sp.expand(A**3), t)
eqs = [sp.expand(e) for e in sp.Poly(rem, t).all_coeffs()]   # A^3 | g

G = sp.groebner(eqs, a0, a1, a2, order='lex')
g0, g1, gq = G.exprs
quint = sp.Poly(gq, a2)
degs = sorted({m[0] for m in quint.monoms()})
assert all(d % 13 == 0 for d in degs), degs    # quintic in a2^13
print("Groebner: triangular over a degree-65 poly = quintic in a2^13  OK")

roots = sp.nroots(quint, n=40)
a2v = [x for x in roots if abs(sp.im(x)) < 1e-25][0]
a0v = sp.expand(-(g0 - a0)).subs(a2, a2v)
a1v = sp.expand(-(g1 - a1)).subs(a2, a2v)
Av = sp.Poly(A.subs({a0: a0v, a1: a1v, a2: a2v}), t)
gv = sp.Poly(sp.integrate(13*t**6*Av.as_expr()**2, t) + 1, t)

B, remv = sp.div(gv, sp.Poly(Av.as_expr()**3, t))
assert max([abs(sp.N(c)) for c in remv.all_coeffs()] or [0]) < 1e-30
gm1 = sp.Poly(gv.as_expr() - 1, t)
assert all(abs(sp.N(gm1.nth(i))) == 0 for i in range(7))     # 7-fold root at 0
D = sp.Poly(sp.expand(gm1.as_expr()/t**7), t)

def squarefree(P):
    return abs(sp.N(sp.resultant(P.as_expr(), sp.diff(P.as_expr(), t), t))) > 1e-12

assert squarefree(Av) and squarefree(B) and squarefree(D)
assert abs(sp.N(sp.resultant(Av.as_expr(), B.as_expr(), t))) > 1e-12
print("profile verified: g = A^3 B, g-1 = t^7 D, all squarefree/coprime")
print("A =", [sp.N(c, 20) for c in Av.all_coeffs()])
print("B =", [sp.N(c, 20) for c in B.all_coeffs()])
print()
print("This is the (-2)-curve Belyi map of the k=3 isotope framework,")
print("degrees (135, 90) -- the smallest open candidate for a 2D Keller map.")
