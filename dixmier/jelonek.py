"""Non-properness (Jelonek) set of the Alpoge map F.

S_F = values approached by fibers escaping to infinity: close the graph
{F(x) = u} in P^3 x C^3, intersect with the hyperplane at infinity W = 0,
project to u-space. Computed by elimination over Q:

  I = < W^{d_i} F_i(X/W, Y/W, Z/W) - u_i W^{d_i},  W > : (X,Y,Z)^inf
  S_F = V( I  eliminate  X,Y,Z,W )

The saturation by (X,Y,Z) removes the irrelevant locus. We do the
saturation crudely by three affine charts X=1, Y=1, Z=1 (covering the
points at infinity) and intersect nothing — union of chart eliminants.
"""
import subprocess
import sys

import sympy as sp

from jc3_map import F

X, Y, Z, W, u1, u2, u3 = sp.symbols('X Y Z W u1 u2 u3')
x, y, z = sp.symbols('x y z')
U = (u1, u2, u3)


def homogenized(f):
    d = sp.total_degree(f, x, y, z)
    return sp.expand(W**d * f.subs({x: X/W, y: Y/W, z: Z/W})), d


def chart_eliminant(chart_var):
    eqs = []
    for f, u in zip(F, U):
        h, d = homogenized(f)
        eqs.append(sp.expand(h - u * W**d))
    eqs.append(W)
    subs = {chart_var: 1}
    eqs = [sp.expand(e.subs(subs)) for e in eqs]
    vars_rem = [v for v in (X, Y, Z, W) if v != chart_var]
    all_vars = vars_rem + [u1, u2, u3]
    ms = ','.join(str(v) for v in all_vars) + '\n0\n' + ',\n'.join(
        str(e).replace('**', '^').replace(' ', '') for e in eqs if e != 0) + '\n'
    open(f'jel_{chart_var}.ms', 'w').write(ms)
    r = subprocess.run(['msolve', '-e', str(len(vars_rem)), '-g', '2',
                        '-f', f'jel_{chart_var}.ms', '-o', f'jel_{chart_var}.out'],
                       capture_output=True, text=True, timeout=3600)
    out = open(f'jel_{chart_var}.out').read()
    print(f'=== chart {chart_var} (rc {r.returncode}):')
    print(out[:1500])
    return out


if __name__ == '__main__':
    for cv in (X, Y, Z):
        chart_eliminant(cv)
