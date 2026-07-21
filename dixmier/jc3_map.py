"""The Alpoge JC_3 counterexample (July 2026) and exact verification.

F: C^3 -> C^3, constant Jacobian -2, not injective.
Source: Wikipedia, "Jacobian conjecture", retrieved 2026-07-20.
"""
import sympy as sp

x, y, z = sp.symbols('x y z')
V = (x, y, z)

F1 = z*(1 + x*y)**3 + y**2*(1 + x*y)*(4 + 3*x*y)
F2 = y + 3*x*(1 + x*y)**2*z + 3*x*y**2*(4 + 3*x*y)
F3 = 2*x - 3*x**2*y - x**3*z
F = (F1, F2, F3)


def jacobian_det():
    J = sp.Matrix([[sp.diff(f, v) for v in V] for f in F])
    return sp.expand(J.det())


def apply_F(pt):
    subs = dict(zip(V, pt))
    return tuple(sp.nsimplify(sp.expand(f.subs(subs))) for f in F)


if __name__ == '__main__':
    d = jacobian_det()
    print('det J =', d)
    p1 = (sp.Integer(0), sp.Integer(0), sp.Rational(-1, 4))
    p2 = (sp.Integer(1), sp.Rational(-3, 2), sp.Rational(13, 2))
    a, b = apply_F(p1), apply_F(p2)
    print('F(0,0,-1/4)      =', a)
    print('F(1,-3/2,13/2)   =', b)
    print('collision:', a == b)
