"""Jelonek set of F, take 2: saturate by W before slicing W=0.

Stage 1: J = <W^d_i F_i(X/W,..) - u_i W^d_i, T W - 1>, eliminate T
         => generators of I : W^inf  (closure of the graph, no W=0 trash).
Stage 2: set W = 0, work in charts X=1 / Y=1 / Z=1, eliminate the two
         remaining infinity coordinates => S_F ideal in (u1,u2,u3).
"""
import subprocess

import sympy as sp

from jc3_map import F

T, X, Y, Z, W, u1, u2, u3 = sp.symbols('T X Y Z W u1 u2 u3')
x, y, z = sp.symbols('x y z')
U = (u1, u2, u3)


def msolve_elim(eqs, vars_order, nelim, tag):
    ms = ','.join(str(v) for v in vars_order) + '\n0\n' + ',\n'.join(
        str(sp.expand(e)).replace('**', '^').replace(' ', '')
        for e in eqs if sp.expand(e) != 0) + '\n'
    open(f'{tag}.ms', 'w').write(ms)
    r = subprocess.run(['msolve', '-e', str(nelim), '-g', '2',
                        '-f', f'{tag}.ms', '-o', f'{tag}.out'],
                       capture_output=True, text=True, timeout=7200)
    out = open(f'{tag}.out').read()
    polys = ''.join(l for l in out.splitlines()
                    if not l.lstrip().startswith('#'))
    polys = polys.strip().rstrip(':').strip()
    if polys.startswith('[') and polys.endswith(']'):
        polys = polys[1:-1]
    return [p for p in polys.split(',') if p.strip()], out


def main():
    base = []
    for f, u in zip(F, U):
        d = sp.total_degree(f, x, y, z)
        base.append(sp.expand(W**d * f.subs({x: X/W, y: Y/W, z: Z/W})
                              - u * W**d))
    # Stage 1: saturation by W via Rabinowitsch elimination of T
    gens, _ = msolve_elim(base + [T*W - 1], [T, X, Y, Z, W, u1, u2, u3],
                          1, 'jel_sat')
    print(f'stage 1: {len(gens)} saturated generators')
    gsyms = {'X': X, 'Y': Y, 'Z': Z, 'W': W, 'u1': u1, 'u2': u2, 'u3': u3}
    gexprs = [sp.sympify(g.replace('^', '**'), locals=gsyms) for g in gens]
    # Stage 2: W = 0, charts
    for chart in (X, Y, Z):
        eqs = [sp.expand(g.subs(W, 0).subs(chart, 1)) for g in gexprs]
        rem = [v for v in (X, Y, Z) if v != chart]
        polys, out = msolve_elim(eqs, rem + [u1, u2, u3], 2,
                                 f'jel2_{chart}')
        print(f'=== chart {chart}: S_F ideal generators:')
        for p in polys[:8]:
            print('   ', p[:200])


if __name__ == '__main__':
    main()
