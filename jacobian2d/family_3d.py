"""Re-derivation of the general 3D family and construction of a NEW instance.

Ansatz (all C^*-equivariant, weights (-1,1,2)):
    gamma = g(w) - t,   beta = 3*u^2*t + b0(w),   alpha = u^3*t + a0(w),  u = 1+w.
Solving  det JF = k (constant)  gives a linear solution space; imposing
polynomiality of the lift forces
    b0(0) = 0,   G1 = -3*G0/2,   B1 = G0/2,
leaving parameters G0 (scale) and G2 free, with

    det JF = -G0^2/2      (independent of G2!).

G0=2, G2=0 is the announced counterexample (degrees (7,6,4)).
G0=2, G2=1 (built below) has degrees (8,7,5) -- NOTE: later shown to be
F o (x,y,z-y^2), i.e. the announced map up to a source shear (REPORT 9.5).

Run: python3 family_3d.py
"""
import sympy as sp

x, y, z, w, t = sp.symbols('x y z w t')
u = 1 + w

def build(G0v, G2v):
    G1v = sp.Rational(-3, 2)*G0v
    B1v = sp.Rational(1, 2)*G0v
    g = G0v + G1v*w + G2v*w**2
    b0 = (B1v*w - 3*G0v*w**2 - 3*G1v*w**3 - 6*G1v*w**2
          - 3*G2v*w**4 - 6*G2v*w**3 - 3*G2v*w**2)
    a0 = (B1v*w**2/4 - B1v/4 - G0v*w**3 - sp.Rational(3, 2)*G0v*w**2
          - sp.Rational(3, 2)*G0v*w - G0v - G1v*w**4 - 3*G1v*w**3
          - sp.Rational(9, 4)*G1v*w**2 - G1v*w - sp.Rational(3, 4)*G1v
          - G2v*w**5 - 3*G2v*w**4 - 3*G2v*w**3 - G2v*w**2)
    sub = {w: x*y, t: x**2*z}
    A = sp.expand(sp.cancel(((u**3*t + a0)/x**2).subs(sub)))
    B = sp.expand(sp.cancel(((3*u**2*t + b0)/x).subs(sub)))
    C = sp.expand((x*(g - t)).subs(sub))
    return A, B, C

for G0v, G2v, label in [(2, 0, "announced map"), (2, 1, "shear-twisted instance")]:
    A, B, C = build(G0v, G2v)
    for f in (A, B, C):
        assert sp.denom(sp.together(f)) == 1     # polynomial
    J = sp.Matrix([[sp.diff(f, v) for v in (x, y, z)] for f in (A, B, C)])
    det = sp.expand(J.det())
    degs = [sp.total_degree(f, x, y, z) for f in (A, B, C)]
    print(f"{label}:  degrees {degs},  det J = {det}")
    assert det == -sp.Rational(G0v**2, 2)

# fiber count of the new instance at a random rational point
A, B, C = build(2, 1)
pt = {x: sp.Rational(1, 3), y: sp.Rational(2, 5), z: sp.Rational(1, 7)}
tgt = [f.subs(pt) for f in (A, B, C)]
sols = sp.solve([sp.Eq(A, tgt[0]), sp.Eq(B, tgt[1]), sp.Eq(C, tgt[2])],
                [x, y, z], dict=True)
print(f"shear-twisted instance: generic fiber has {len(sols)} points  => non-injective")
assert len(sols) >= 2
