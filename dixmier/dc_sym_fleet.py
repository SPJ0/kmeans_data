"""High-B sweep of Fourier-symmetric (binary dihedral) DC_1 cells.

Cells: (B, d, orientation, corner, sign) with Bernstein bidegrees (2B, 3B),
sublattice step d >= 3, Fourier (anti)invariance. Any NONEMPTY cell is a
counterexample to DC_1 — and hence to JC_2. Starts at B = 17 (B <= 16 closed
by the full sublattice layer).

Usage: python3 dc_sym_fleet.py [ncores] [Bmin] [Bmax]
"""
import multiprocessing as mp
import os
import subprocess
import sys
import time

import sympy as sp

from dc_sym import cell_system

NCORES = int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()
BMIN = int(sys.argv[2]) if len(sys.argv) > 2 else 17
BMAX = int(sys.argv[3]) if len(sys.argv) > 3 else 24


def to_msolve(eqs, vars_):
    lines = [','.join(str(v) for v in vars_), '0']
    body = [str(sp.expand(e)).replace('**', '^').replace(' ', '') for e in eqs]
    return '\n'.join(lines) + '\n' + ',\n'.join(body) + '\n'


def run_cell(job):
    B, d, degP, degQ, corner, sign = job
    sgn = 'p' if sign == '+' else 'm'
    tag = f'DCD_B{B}_S{d}_{degP}_{degQ}_{corner}_{sgn}'
    t0 = time.time()
    try:
        eqs, vars_ = cell_system(d, degP, degQ, corner, sign)
        fin, fout = f'cell_{tag}.ms', f'cell_{tag}.out'
        open(fin, 'w').write(to_msolve(eqs, vars_))
        r = subprocess.run(['msolve', '-g', '2', '-t', '2', '-f', fin, '-o', fout],
                           capture_output=True, text=True, timeout=48*3600)
        out = open(fout).read() if os.path.exists(fout) else ''
        body = ''.join(l.strip() for l in out.splitlines()
                       if not l.lstrip().startswith('#')).replace(' ', '')
        if not body:
            verdict = 'FAILED_NO_OUTPUT'
        elif body.rstrip(':,;') == '[1]':
            verdict = 'EMPTY'
        else:
            verdict = 'NONEMPTY?!'
        return f'{tag}: {verdict} [{len(vars_)} vars, {len(eqs)} eqs, {time.time()-t0:.0f}s]'
    except Exception as ex:
        return f'{tag}: FAILED {type(ex).__name__}: {str(ex)[:120]} [{time.time()-t0:.0f}s]'


def main():
    jobs = []
    for B in range(BMIN, BMAX + 1):
        for d in range(3, B + 1):
            for (a, b) in ((2*B, 3*B), (3*B, 2*B)):
                for corner in ('extreme', 'w0'):
                    for sign in ('+', '-'):
                        jobs.append((B, d, a, b, corner, sign))
    jobs.sort(key=lambda j: (j[0], -j[1]))
    print(f'{len(jobs)} dihedral DC cells, B={BMIN}..{BMAX}, {NCORES} workers',
          flush=True)
    with mp.Pool(min(NCORES, len(jobs))) as pool:
        with open('dc_sym_results.log', 'a') as f:
            for line in pool.imap_unordered(run_cell, jobs):
                print(line, flush=True)
                f.write(line + '\n')
                f.flush()
                if 'NONEMPTY' in line:
                    print('!!! POTENTIAL DC_1 (=> JC_2) COUNTEREXAMPLE CELL !!!',
                          flush=True)
    print('dc dihedral fleet complete', flush=True)


if __name__ == '__main__':
    main()
