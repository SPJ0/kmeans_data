"""Monodromy of the Alpoge map F: Z/3 (cyclic) vs S_3.

The degree-3 extension C(x,y,z) / F*C(x,y,z) has square discriminant iff its
Galois closure is cyclic. The discriminant is a rational function of the
target; if it is a square in the function field, EVERY rational
specialization is a rational square. So: sample many random integer targets,
compute the fiber's eliminating cubic via msolve -P 2, and check whether its
discriminant is a perfect square in Q.

All squares across many samples -> overwhelming evidence for Z/3 (then worth
certifying exactly); any nonsquare at a generic target -> S_3, proven.
"""
import ast
import random
import subprocess
import sys

import sympy as sp

from jc3_map import F

random.seed(42)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20


def fiber_cubic(target):
    eqs = [sp.expand(f - t) for f, t in zip(F, target)]
    ms = 'x,y,z\n0\n' + ',\n'.join(
        str(e).replace('**', '^').replace(' ', '') for e in eqs) + '\n'
    open('probe.ms', 'w').write(ms)
    subprocess.run(['msolve', '-P', '2', '-f', 'probe.ms', '-o', 'probe.out'],
                   capture_output=True, text=True, timeout=600)
    raw = open('probe.out').read().strip().rstrip(':')
    data = ast.literal_eval(raw)
    # data = [dim, [nvars?, deg, deg, vars, lin form, [1, [[deg, coeffs], ...]]]]
    body = data[1]
    if data[0] != 0:
        return None, f'dim={data[0]}'
    elim = body[5][1][0]  # [degree, [c0..cdeg]] ascending coeffs
    deg, coeffs = elim[0], elim[1]
    T = sp.Symbol('T')
    poly = sum(sp.Integer(c) * T**i for i, c in enumerate(coeffs))
    return sp.Poly(poly, T), None


def main():
    verdicts = []
    for i in range(N):
        target = tuple(random.randint(-50, 50) for _ in range(3))
        try:
            poly, err = fiber_cubic(target)
        except Exception as ex:
            print(f'{target}: parse/run error {ex}')
            continue
        if poly is None or poly.degree() != 3:
            print(f'{target}: skip ({err or f"deg {poly.degree()}"} — '
                  f'special target)')
            continue
        disc = sp.discriminant(poly.as_expr(), sp.Symbol('T'))
        sq = sp.sqrt(sp.Rational(disc))
        is_sq = sq.is_rational
        verdicts.append(is_sq)
        print(f'{target}: disc {"IS" if is_sq else "NOT"} a square   '
              f'(disc={disc})')
        sys.stdout.flush()
    n_sq = sum(verdicts)
    print(f'\n{n_sq}/{len(verdicts)} square discriminants')
    if verdicts and n_sq == len(verdicts):
        print('=> monodromy almost certainly Z/3 (cyclic); certify exactly next')
    elif verdicts:
        print('=> monodromy S_3 (non-square disc at a generic rational target)')


if __name__ == '__main__':
    main()
