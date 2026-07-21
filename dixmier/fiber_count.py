"""Count preimages of a generic target under the Alpoge map F.

Emits the fiber system F(v) = (a,b,c) in msolve format and runs msolve's
rational-parametrization mode; the degree of the parametrization = number of
complex preimages (generic target => reduced fiber). Expect 3 if F is 3-to-1.
"""
import subprocess
import sys

import sympy as sp

from jc3_map import F, V

a, b, c = (int(t) for t in sys.argv[1:4]) if len(sys.argv) > 3 else (3, 5, 7)
eqs = [sp.expand(F[0] - a), sp.expand(F[1] - b), sp.expand(F[2] - c)]
ms = 'x,y,z\n0\n' + ',\n'.join(
    str(e).replace('**', '^').replace(' ', '') for e in eqs) + '\n'
open('fiber.ms', 'w').write(ms)
for mode in (['-P', '2'], ['-g', '2']):
    r = subprocess.run(['msolve'] + mode + ['-f', 'fiber.ms', '-o', 'fiber.out'],
                       capture_output=True, text=True, timeout=3600)
    print('=== msolve', ' '.join(mode), '-> rc', r.returncode)
    print(open('fiber.out').read()[:2000])
