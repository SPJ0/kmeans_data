"""Targeted JC_2 construction shot: coset-graded Keller pair + imposed collision.

Ansatz (2D transplant of the Alpöge mechanism): with weight w = deg_x - deg_y,
  p supported in w ≡ +1 (mod d), total degree <= degP,
  q supported in w ≡ -1 (mod d), total degree <= degQ,
  jac(p,q) = 1,
  f(v) = f(v') for two points v = (x1,y1) != v' = (x2,y2)  (saturated),
  corner saturation on the leading coset coefficients.
A solution is a non-injective Keller map: a counterexample to JC_2.

Usage: python3 jc2_construct.py d degP degQ [tag]
Small (d, deg <= 100) runs MUST come back EMPTY (Moh): plumbing validation.
"""
import subprocess
import sys

import sympy as sp

x, y = sp.symbols('x y')


GRADE = (1, -1)  # (alpha, beta): weight of x^i y^j is alpha*i + beta*j


def coset_element(name, degmax, d, coset):
    al, be = GRADE
    syms, expr = [], sp.Integer(0)
    for i in range(degmax + 1):
        for j in range(degmax + 1 - i):
            if (al*i + be*j - coset) % d != 0:
                continue
            c = sp.Symbol(f'{name}_{i}_{j}')
            syms.append(c)
            expr += c * x**i * y**j
    return expr, syms


def build(d, degP, degQ, a=1):
    al, be = GRADE
    # jac(coset a, coset b) lands in coset a + b - (al+be); jac = 1 needs
    # that to be 0 mod d, so q's coset is (al+be) - a.
    P, ps = coset_element('p', degP, d, a)
    Q, qs = coset_element('q', degQ, d, (al + be) - a)
    jac = sp.diff(P, x)*sp.diff(Q, y) - sp.diff(P, y)*sp.diff(Q, x)
    eqs = list(sp.Poly(sp.expand(jac - 1), x, y).coeffs())
    x1, y1, x2, y2, T0, T1, T2 = sp.symbols('x1 y1 x2 y2 T0 T1 T2')
    # collision: f(v) = f(v'), v != v'. The diagonal is excluded by
    # T0*(x1-x2) = 1 (variant 'dx') or T0*(y1-y2) = 1 (variant 'dy');
    # together the two variants cover every off-diagonal collision.
    for E in (P, Q):
        eqs.append(sp.expand(E.subs({x: x1, y: y1}) - E.subs({x: x2, y: y2})))
    eqs.append(sp.expand(T0*(x1 - x2) - 1) if COLL == 'dx'
               else sp.expand(T0*(y1 - y2) - 1))
    # corner saturation: pin opposite Newton-polygon corners (max-x monomial
    # of p, max-y monomial of q)
    def corner(syms_list, key):
        pairs = [tuple(int(t) for t in str(s).split('_')[1:]) for s in syms_list]
        return max(pairs, key=key)
    ci, cj = corner(ps, lambda ij: (ij[0], -ij[1]))
    di, dj = corner(qs, lambda ij: (ij[1], -ij[0]))
    eqs.append(sp.Symbol(f'p_{ci}_{cj}')*T1 - 1)
    eqs.append(sp.Symbol(f'q_{di}_{dj}')*T2 - 1)
    vars_ = ps + qs + [x1, y1, x2, y2, T0, T1, T2]
    return eqs, vars_


COLL = 'dx'


def main():
    global COLL, GRADE
    d, degP, degQ = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    COLL = sys.argv[4] if len(sys.argv) > 4 else 'dx'
    a = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    if len(sys.argv) > 7:
        GRADE = (int(sys.argv[6]), int(sys.argv[7]))
    g = f'g{GRADE[0]}_{GRADE[1]}'.replace('-', 'm')
    tag = f'CONSTRUCT_d{d}_{degP}_{degQ}_{COLL}_a{a}_{g}'
    eqs, vars_ = build(d, degP, degQ, a)
    print(f'{tag}: {len(vars_)} vars, {len(eqs)} eqs', flush=True)
    ms = ','.join(str(v) for v in vars_) + '\n0\n' + ',\n'.join(
        str(sp.expand(e)).replace('**', '^').replace(' ', '')
        for e in eqs if sp.expand(e) != 0) + '\n'
    open(f'cell_{tag}.ms', 'w').write(ms)
    r = subprocess.run(['msolve', '-g', '2', '-t', '4', '-f', f'cell_{tag}.ms',
                        '-o', f'cell_{tag}.out'],
                       capture_output=True, text=True, timeout=48*3600)
    out = open(f'cell_{tag}.out').read()
    body = ''.join(l.strip() for l in out.splitlines()
                   if not l.lstrip().startswith('#')).replace(' ', '')
    verdict = 'EMPTY' if body.rstrip(':,;') == '[1]' else \
        ('NO_OUTPUT' if not body else 'NONEMPTY?! — COUNTEREXAMPLE CANDIDATE')
    print(f'{tag}: {verdict}', flush=True)


if __name__ == '__main__':
    main()
