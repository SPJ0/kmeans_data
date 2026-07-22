"""Trap-hunt round 1 on Sigma' = {A o F = 1}: ALL natural functions dodge.

The AMS/Epimorphism trap needs a regular function on Sigma' with a reduced
IRREDUCIBLE A^1-fiber (and a non-A^1 fiber).  Tested candidates and outcomes:

 x   : fiber over 0 = double cover of C*_y branched via disc y^4(y^2+12):
       a punctured conic, not A^1.  (In (y, W=z+4y^2)-coordinates the fiber is
       quadratic in W.)
 u   : fiber over 0 (i.e. Sigma' n {xy=-1}): z is rational in y with poles at
       (2y^3-1)^3 -- iso C* minus 3 points, not A^1.
 y=0 : irreducible section of total degree 13, leading form -27 x^6 z^7:
       passes through BOTH coordinate points at infinity => >= 2 places at
       infinity => not A^1.
 z=0 : same, degree 36, leading form -59049 x^14 y^22 => not A^1.
 B o F: base curves {A=1, B=beta} eliminate to (xy+1)^2 * N_beta with the
       u^2-factor SPURIOUS (A = u(...) = 0 != 1 on u=0); the genuine base is
           N_beta :  x (y^2 - beta y + 3) + (y - beta) = 0,
       rational, iso A^1 minus the two roots of q(y)=y^2-beta y+3 (q(beta)=3!=0
       so the poles are genuine; at beta^2=12 the two merge to one).  ANY
       component of the etale preimage would give a dominant map A^1 -> (line
       minus >=1 point), i.e. a nonvanishing nonconstant polynomial: impossible.
       B o F dodges for ALL beta, structurally.
 C o F: base curves {A=1, C=lam} are PLANE CUBICS in (x, v=xy):
           -lam (1+v)^3 + x (1+v)(v+2) - x^3 = 0
       (checked: res_z has total degree 3 in (x,v)).  Smooth cubic => genus 1
       => no rational curve dominates it; singular lam-values give punctured
       rational curves missing >=2 points => unit argument kills A^1-components;
       lam=0 is reducible (C = -x(x^2 z + 3xy - 2)) => Epimorphism inapplicable.
       C o F dodges for ALL lam.

STRUCTURAL REASON (the meta-insight):  on Sigma', A o F = 1 forces the units
u = 1+xy and 1+AB to be NONVANISHING.  These activated units puncture every
natural base curve, and punctured bases cannot support A^1-fibers (the unit
argument).  The same unit-rigidity of A^2 that blocks naive 2D constructions
PROTECTS this candidate from the AMS trap.

STATUS.  Sigma' survives all known obstructions (9 sheets > all sheet-count
theorems) and all round-1 traps.  Sigma' iso A^2  <=>  JC(2) false remains
open; deciding it needs the positive program: an explicit A^1-fibration on
Sigma' (which with Cl=0, units=C*, would give iso A^2 via Miyanishi-Sugie),
or a kappa-bar computation.

Run: python3 traphunt_sigma_prime.py
"""
import sympy as sp

x, y, z, W, lam, beta = sp.symbols('x y z W lambda beta')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')
At = (1 + a*b)**3*c + b**2*(1 + a*b)*(4 + 3*a*b)
AF1 = At.subs({a: A, b: B, c: C}, simultaneous=True) - 1

# x = 0 fiber: quadratic in W with discriminant y^4(y^2+12)
f0W = sp.expand(AF1.subs(x, 0).subs(z, W - 4*y**2))
assert sp.degree(f0W, W) == 2
assert sp.factor(sp.discriminant(sp.Poly(f0W, W))) == y**4*(y**2 + 12)
print("x=0 fiber: punctured conic cover, not A^1  OK")

# u = 0 fiber: poles at (2y^3-1)^3
AFu = sp.together(At.subs({a: y**2, b: -2*y, c: -5/y + z/y**3},
                          simultaneous=True) - 1)
zsol = sp.solve(sp.Eq(sp.numer(AFu), 0), z)[0]
assert sp.factor(sp.denom(sp.together(zsol))) == (2*y**3 - 1)**3
print("u=0 fiber: C* minus 3 points, not A^1  OK")

# coordinate sections: >= 2 places at infinity
def leading_form(f, vs):
    d = sp.total_degree(f, *vs)
    return sp.factor(sum(t for t in sp.Add.make_args(sp.expand(f))
                         if sp.total_degree(t, *vs) == d))
AFy0 = sp.expand(At.subs({a: z, b: 3*x*z, c: 2*x - x**3*z},
                         simultaneous=True) - 1)
assert leading_form(AFy0, (x, z)) == -27*x**6*z**7
Fz0 = [f.subs(z, 0) for f in (A, B, C)]
AFz0 = sp.expand(At.subs({a: Fz0[0], b: Fz0[1], c: Fz0[2]},
                         simultaneous=True) - 1)
assert leading_form(AFz0, (x, y)) == -59049*x**14*y**22
print("y=0 and z=0 sections: two places at infinity, not A^1  OK")

# B o F base curves: (xy+1)^2 spurious x genuine punctured-rational core
R = sp.factor(sp.resultant(A - 1, B - beta, z))
assert R == (x*y + 1)**2*(-beta*x*y - beta + x*y**2 + 3*x + y)
print("B∘F bases: A^1 minus roots of y^2-beta*y+3; unit argument kills A^1  OK")

# C o F base curves: plane cubics in (x, v=xy)
Rc = sp.expand(sp.resultant(A - 1, C - lam, z))
v = sp.Symbol('v')
cubic = sp.expand(-lam*(1 + v)**3 + x*(1 + v)*(v + 2) - x**3)
assert sp.simplify(Rc - cubic.subs(v, x*y)) == 0
assert sp.total_degree(cubic, x, v) == 3
print("C∘F bases: plane cubics (genus <= 1); no A^1-components  OK")
print("ROUND 1 COMPLETE: Sigma' survives every trap. Dichotomy still open:")
print("  Sigma' iso A^2  <=>  JC(2) false.")
