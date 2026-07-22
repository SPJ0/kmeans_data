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
