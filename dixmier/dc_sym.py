"""Fourier-symmetric (binary dihedral) cells for DC_1.

The Fourier automorphism om of A_1: x -> d, d -> -x. In GWA data
{w: p_w(theta)} it acts by
    om(P)_w = s_w * p_{-w}(-theta-1),   s_w = 1 (w<=0), (-1)^w (w>0),
since om(theta) = -theta-1, om(x^w) = d^w, om(d^c) = (-1)^c x^c.

Together with the sublattice torus group g_d this generates a binary
dihedral group Gamma (nonabelian for d>=3). P,Q om- and g_d-(semi)invariant
with [Q,P]=1 lie in a proper invariant subalgebra: free non-generation,
exactly as in the commutative case. sign='+' is Gamma-invariance; sign='-'
is the character twist om(P)=-P (subalgebra generated lies in A_1^ker(chi)).

Self-test: om is an algebra automorphism, om(theta)=-theta-1, om^2=parity.
"""
import sympy as sp

from weyl import t, mul, comm, clean
from cascade2 import cell_system as base_cell_system


def fourier(e):
    out = {}
    for w, p in e.items():
        s = sp.Integer(1) if w <= 0 else sp.Integer(-1)**w
        out[-w] = sp.expand(s * p.subs(t, -t - 1))
    return clean(out)


def sym_constraints(name, degmax, wrange, sign):
    """p_w(t) = sign * s_w * p_{-w}(-t-1) as linear eqs in the coefficients."""
    def poly_of(w):
        db = (degmax - abs(w)) // 2
        if w not in wrange or db < 0:
            return sp.Integer(0)
        return sum(sp.Symbol(f'{name}_{w}_{j}') * t**j for j in range(db + 1))
    eqs = []
    sgn = sp.Integer(1) if sign == '+' else sp.Integer(-1)
    for w in wrange:
        s = sp.Integer(1) if w <= 0 else sp.Integer(-1)**w
        diff = sp.expand(poly_of(w) - sgn * s * poly_of(-w).subs(t, -t - 1))
        if diff != 0:
            eqs.extend(sp.Poly(diff, t).all_coeffs())
    return [e for e in eqs if e != 0]


def cell_system(d, degP, degQ, corner='extreme', sign='+'):
    eqs, vars_ = base_cell_system(d, degP, degQ, corner)
    wP = [w for w in range(-degP, degP + 1) if w % d == 0]
    wQ = [w for w in range(-degQ, degQ + 1) if w % d == 0]
    eqs = eqs + sym_constraints('p', degP, wP, sign) \
              + sym_constraints('q', degQ, wQ, sign)
    return eqs, vars_


if __name__ == '__main__':
    import random
    random.seed(7)
    # om(theta) = -theta-1
    assert fourier({0: t}) == {0: sp.expand(-t - 1)}
    for _ in range(25):
        e1 = {random.randint(-3, 3):
              sp.Integer(random.randint(-2, 2))*t**random.randint(0, 2)
              + random.randint(-2, 2)}
        e2 = {random.randint(-3, 3):
              sp.Integer(random.randint(-2, 2))*t**random.randint(0, 2)
              + random.randint(-2, 2)}
        lhs, rhs = fourier(mul(e1, e2)), mul(fourier(e1), fourier(e2))
        ws = set(lhs) | set(rhs)
        assert all(sp.expand(lhs.get(w, 0) - rhs.get(w, 0)) == 0 for w in ws), \
            (e1, e2)
        par = fourier(fourier(e1))
        exp = {w: sp.expand(p * sp.Integer(-1)**abs(w)) for w, p in
               clean(e1).items()}
        assert par == exp, (e1, par, exp)
    print('fourier validated: automorphism on 25 random products, om^2 = parity')
