"""Verification of the Alpoge/Fable counterexample to the Jacobian conjecture in dim 3.

Announced 2026-07-20.  F = (a,b,c): C^3 -> C^3 below satisfies det JF = -2
(a Keller map) yet is generically 3-to-1; in particular three distinct points
map to (-1/4, 0, 0).  Hence the Jacobian conjecture is FALSE for n >= 3.

Run: python3 verify_3d_counterexample.py
"""
import sympy as sp

x, y, z = sp.symbols('x y z')
u = 1 + x*y

a = u**3*z + y**2*u*(4 + 3*x*y)
b = y + 3*x*u**2*z + 3*x*y**2*(4 + 3*x*y)
c = 2*x - 3*x**2*y - x**3*z

J = sp.Matrix([[sp.diff(f, v) for v in (x, y, z)] for f in (a, b, c)])
det = sp.expand(J.det())
assert det == -2, det
print("det J = -2  (constant)  OK")

pts = [(0, 0, sp.Rational(-1, 4)),
       (1, sp.Rational(-3, 2), sp.Rational(13, 2)),
       (-1, sp.Rational(3, 2), sp.Rational(13, 2))]
for p in pts:
    img = tuple(sp.simplify(f.subs(dict(zip((x, y, z), p)))) for f in (a, b, c))
    assert img == (sp.Rational(-1, 4), 0, 0), (p, img)
    print(f"F{p} = (-1/4, 0, 0)  OK")

# C^*-equivariance: weights x:-1, y:1, z:2 (source), a:2, b:1, c:-1 (target)
lam = sp.symbols('lam', nonzero=True)
scal = {x: lam*x, y: y/lam, z: z/lam**2}
for f, wt in ((a, 2), (b, 1), (c, -1)):
    assert sp.simplify(f.subs(scal, simultaneous=True) - lam**(-wt)*f) == 0
print("weighted homogeneity (x,y,z) ~ (-1,1,2), (a,b,c) ~ (2,1,-1)  OK")
print("All checks passed: Keller, non-injective => JC(3) is false.")
