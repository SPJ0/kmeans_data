"""Commutative (classical) analog of cascade2: JC_2 cells.

A planar Keller counterexample is a pair P,Q in C[x,y] with
jac(P,Q) := P_x Q_y - P_y Q_x = 1 and C[P,Q] != C[x,y] (a Keller map is
invertible iff P,Q generate). Under the torus grading wt(x)=1, wt(y)=-1
(wt(x^a y^b) = a-b), the weight-w component is (xy)^j x^w (w>=0) or
(xy)^j y^-w (w<0), and jac respects the grading. If P,Q are supported in
weights dZ with d>=2 they lie in the proper subalgebra S_d — free
non-generation certificate, exactly as in the Weyl/Dixmier case. GGV's
planar wall likewise gives gcd(deg P, deg Q) >= 16.

Cell = (d, degP, degQ, corner): total-degree caps, corner saturation as in
cascade2 ('extreme' = x^degP / x^degQ coefficient forced nonzero, 'w0' =
(xy)^(deg/2) coefficient forced nonzero). Verdict via Groebner: [1] <=>
cell provably EMPTY over C.
"""
import sys
import time

import sympy as sp

x, y = sp.symbols('x y')


def cell_system(d, degP, degQ, corner='extreme'):
    syms = []

    def make(name, degmax, wrange):
        expr = sp.Integer(0)
        for w in wrange:
            db = (degmax - abs(w)) // 2
            if db < 0:
                continue
            vw = x**w if w >= 0 else y**(-w)
            for j in range(db + 1):
                c = sp.Symbol(f'{name}_{w}_{j}')
                syms.append(c)
                expr += c * (x*y)**j * vw
        return expr

    wP = [w for w in range(-degP, degP + 1) if w % d == 0]
    wQ = [w for w in range(-degQ, degQ + 1) if w % d == 0]
    P = make('p', degP, wP)
    Q = make('q', degQ, wQ)
    jac = sp.diff(P, x)*sp.diff(Q, y) - sp.diff(P, y)*sp.diff(Q, x)
    poly = sp.Poly(sp.expand(jac - 1), x, y)
    eqs = list(poly.coeffs())
    T1, T2 = sp.symbols('T1 T2')
    if corner == 'extreme':
        # true corner of the cell: largest weight actually present
        wpm, wqm = (degP // d) * d, (degQ // d) * d
        sat = [sp.Symbol(f'p_{wpm}_0')*T1 - 1, sp.Symbol(f'q_{wqm}_0')*T2 - 1]
    else:  # weight-0 dominant: top (xy)-coefficients at w=0
        sat = [sp.Symbol(f'p_0_{degP//2}')*T1 - 1,
               sp.Symbol(f'q_0_{degQ//2}')*T2 - 1]
    return [sp.expand(e) for e in eqs] + sat, syms + [T1, T2]


def run(d, degP, degQ, corner):
    t0 = time.time()
    eqs, vars_ = cell_system(d, degP, degQ, corner)
    tb = time.time() - t0
    G = sp.groebner(eqs, *vars_, order='grevlex')
    verdict = 'EMPTY' if list(G.exprs) == [sp.Integer(1)] \
        else f'NONEMPTY (basis {len(G.exprs)})'
    print(f'JC2 S_{d} cell ({degP},{degQ}) corner={corner:8s}: {verdict}   '
          f'[{len(vars_)} vars, {len(eqs)} eqs, build {tb:.0f}s, '
          f'total {time.time()-t0:.0f}s]')
    sys.stdout.flush()
    return G


if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'control':
        # d=1 (1,1) extreme contains linear automorphism pairs (e.g. P=x,
        # Q=y): must come back NONEMPTY, validating the builder.
        run(1, 1, 1, 'extreme')
    elif which == 's2':
        run(2, 4, 6, 'extreme'); run(2, 4, 6, 'w0')
    elif which == 's4':
        run(4, 8, 12, 'extreme'); run(4, 8, 12, 'w0')
