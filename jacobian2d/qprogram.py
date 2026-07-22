"""The q-program: curved-graph candidates {C = q(A,B)} and the design calculus.

CANDIDATES.  For q in C[a,b], the surface  S_q = {C = q(A,B)}  =  F^{-1}(W_q),
W_q = {z = q(x,y)} iso A^2, carries a 3:1 etale map to W_q.  Structural dodges
for EVERY q:  K_q = c - q(a,b) is linear in c, hence irreducible -- no units
kill;  the u-trap fires iff (b - b0) | q for some b0 != 0 -- trivially avoided;
the A-trap needs a fiber-curve inside the Jelonek set -- avoided generically.
The only remaining test is the Euler characteristic, and the whole question
reduces to a DESIGN CALCULUS:

    e(S_q) = 3 - 2 e(V_q) - #deep(q),
    V_q  = {Lam*(a, b, q(a,b)) = 0}     (the deficiency curve),
    deep = points of V_q with 4 - 3 b q = 0 (fiber drops to zero preimages).

(Verified: q = b^2 gives e(V) = -2, #deep = 3, e = 4 -- matching the full
A-fibration machinery.  An earlier scan reporting e = 1 across simple q's
overcounted #deep by intersection multiplicity; the deep tangencies below
explain why the multiplicity is always 2.)

STRUCTURAL IDENTITIES (new, and the heart of the calculus):

 1. On the deep surface {4 = 3bc}:   Lam* = (12a - b^2)^2 / (3 b^2)
    -- a PERFECT SQUARE.  Hence deep points are exactly
    {3 b q = 4} n {12a = b^2}, and every graph crossing is forcibly TANGENT
    (multiplicity 2), which is why naive resultant counts double them.
 2. disc_c(Lam*) = (b^2 - 12a)^3 -- a PERFECT CUBE.  Consequently the Jelonek
    surface J = {Lam* = 0} is RATIONAL with explicit parametrization
        a = (b^2 - s^2)/12,     c = (4/3)(b + 2s)/(b + s)^2 ,
    (branch s -> -s), and V_q becomes the explicit plane curve
        4(b + 2s) = 3 (b+s)^2 * q((b^2-s^2)/12, b)        (minus {b+s=0}).
 3. THE (12a - b^2)-TRICK:  q = (12a - b^2) h  =>  R_q = 3bq - 4 = -4 on the
    parabola: NO deep points, for every h.  The design equation collapses to
        e(S_q) = 1   <=>   e(V_q) = 1.
    For constant h = t: V_q has b-discriminant 16 + 48 t s^3 (three simple
    branch points): genus 1, e(V) = -2, e(S_q) = 7 (verified numerically for
    seven values of t).  The open design problem: choose h(a,b) making the
    curve 4(b+2s) + 3(b+s)^2 s^2 h = 0 have Euler characteristic 1.

STATUS.  e-landscape so far (first-level surfaces, 3:1):
    q = kb^2: 4;  q = b^3: 5(*);  q = a: 4;  q = ab: 13;  q = b^2+b: 6;
    q = b^2+a: 10;  q = t(12a-b^2): 7.
(*) values from the corrected full machinery / design formula.
No e = 1 yet; the parametrized h-hunt in the (s,b)-coordinates is the next
step.  CAVEAT: a first-level e = 1 candidate would be 3-sheeted, where
Orevkov's theorem (exact statement still to be verified from the original
paper) may apply; the second-level (9:1) lift of this calculus is the
Orevkov-free arena.

Run: python3 qprogram.py  (verifies the identities)
"""
import sympy as sp

a, b, c, s, h = sp.symbols('a b c s h')
Lam = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2

# identity 1: Lam* on {c = 4/(3b)} is (12a-b^2)^2/(3b^2)
lhs = sp.together(Lam.subs(c, sp.Rational(4,3)/b))
assert sp.simplify(lhs - (12*a - b**2)**2/(3*b**2)) == 0
print("1. Lam*|_deep = (12a - b^2)^2 / (3b^2)  OK")

# identity 2: disc_c(Lam*) = (b^2 - 12a)^3
disc = sp.discriminant(sp.Poly(Lam, c))
assert sp.expand(disc - (b**2 - 12*a)**3) == 0
print("2. disc_c(Lam*) = (b^2 - 12a)^3  OK")

# identity 3: the rational parametrization of the Jelonek surface
aP = (b**2 - s**2)/12
cP = sp.Rational(4,3)*(b + 2*s)/(b + s)**2
assert sp.simplify(Lam.subs({a: aP, c: cP}, simultaneous=True)) == 0
print("3. J parametrized by a = (b^2-s^2)/12, c = (4/3)(b+2s)/(b+s)^2  OK")

# identity 4: V_q in (s,b)-coordinates for q = (12a - b^2)*h
q = (12*a - b**2)*h
eq = sp.simplify((cP - q.subs(a, aP))* (b+s)**2 * 3)
expected = 4*(b + 2*s) + 3*(b+s)**2*s**2*h
assert sp.simplify(sp.expand(eq - expected)) == 0
print("4. V_q: 4(b+2s) + 3(b+s)^2 s^2 h = 0  (q = (12a-b^2)h)  OK")

# the (12a-b^2)-trick: no deep points
Rq = sp.expand(3*b*q.subs(a, b**2/12) - 4)
assert Rq == -4
print("5. q = (12a-b^2)h: R_q = -4, zero deep points for every h  OK")
print("Design equation for this family:  e(S_q) = 3 - 2 e(V_q);  target e(V_q) = 1.")
