"""Positive control for the coset-collision construction pipeline.

Encode the 3D analog at exactly the Alpöge shape: components in cosets
(1,-1,1) of 3Z under weights (1,-1,1), degree caps (7,6,4), det J = c != 0
(saturated), one collision with x1 != x2 (saturated). The Alpöge map IS a
solution, so the system MUST come back NONEMPTY — validating that the
encoding finds counterexamples when they exist.
"""
import subprocess
import sys

import sympy as sp

x, y, z = sp.symbols('x y z')
W = (1, -1, 1)          # torus weights of (x, y, z)
COSETS = (1, -1, 1)     # coset of each component mod d
D = 3
CAPS = (7, 6, 4)


def coset_element(name, cap, coset):
    syms, expr = [], sp.Integer(0)
    for i in range(cap + 1):
        for j in range(cap + 1 - i):
            for k in range(cap + 1 - i - j):
                if (W[0]*i + W[1]*j + W[2]*k - coset) % D != 0:
                    continue
                c = sp.Symbol(f'{name}_{i}_{j}_{k}')
                syms.append(c)
                expr += c * x**i * y**j * z**k
    return expr, syms


def main():
    comps, allsyms = [], []
    for n, (cap, cs) in enumerate(zip(CAPS, COSETS)):
        e, s = coset_element(f'f{n}', cap, cs)
        comps.append(e)
        allsyms.extend(s)
    J = sp.Matrix([[sp.diff(f, v) for v in (x, y, z)] for f in comps])
    c0, T0, T1 = sp.symbols('c0 T0 T1')
    eqs = list(sp.Poly(sp.expand(J.det() - c0), x, y, z).coeffs())
    p1 = sp.symbols('a1 a2 a3')
    p2 = sp.symbols('b1 b2 b3')
    s1 = dict(zip((x, y, z), p1))
    s2 = dict(zip((x, y, z), p2))
    for f in comps:
        eqs.append(sp.expand(f.subs(s1) - f.subs(s2)))
    eqs.append(T0*(p1[0] - p2[0]) - 1)   # collision points differ in x
    eqs.append(T1*c0 - 1)                # Jacobian constant nonzero
    vars_ = allsyms + [c0] + list(p1) + list(p2) + [T0, T1]
    print(f'control: {len(vars_)} vars, {len(eqs)} eqs', flush=True)
    ms = ','.join(str(v) for v in vars_) + '\n0\n' + ',\n'.join(
        str(sp.expand(e)).replace('**', '^').replace(' ', '')
        for e in eqs if sp.expand(e) != 0) + '\n'
    open('cell_CONTROL3D.ms', 'w').write(ms)
    r = subprocess.run(['msolve', '-g', '2', '-t', '4',
                        '-f', 'cell_CONTROL3D.ms', '-o', 'cell_CONTROL3D.out'],
                       capture_output=True, text=True, timeout=24*3600)
    out = open('cell_CONTROL3D.out').read()
    body = ''.join(l.strip() for l in out.splitlines()
                   if not l.lstrip().startswith('#')).replace(' ', '')
    if body.rstrip(':,;') == '[1]':
        print('control: EMPTY — PIPELINE BUG, the Alpöge map is a solution!')
    elif body:
        print('control: NONEMPTY as required — pipeline validated '
              f'(basis nontrivial, {len(body)} chars)')
    else:
        print('control: NO_OUTPUT (msolve failed)')


if __name__ == '__main__':
    main()
