"""High-B sweep of binary-dihedral-invariant JC_2 cells.

Cells: (B, d, orientation, corner) with bidegrees (2B, 3B), sublattice step
d >= 3, plus invariance under the symplectic swap — the invariant ring of the
binary dihedral group. Any NONEMPTY cell is a JC_2 counterexample (free
non-generation). Layers B <= 16 are already excluded by the full sublattice
sweep, so this starts at B = 17 and climbs while systems stay tractable.

Usage: python3 jc2_sym_fleet.py [ncores] [Bmin] [Bmax]
"""
import multiprocessing as mp
import os
import subprocess
import sys
import time

import sympy as sp

from jc2_cascade import cell_system

NCORES = int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()
BMIN = int(sys.argv[2]) if len(sys.argv) > 2 else 17
BMAX = int(sys.argv[3]) if len(sys.argv) > 3 else 32


def to_msolve(eqs, vars_):
    lines = [','.join(str(v) for v in vars_), '0']
    body = [str(sp.expand(e)).replace('**', '^').replace(' ', '') for e in eqs]
    return '\n'.join(lines) + '\n' + ',\n'.join(body) + '\n'


def parse_out(fout):
    if not os.path.exists(fout):
        return None
    out = open(fout).read()
    body = ''.join(l.strip() for l in out.splitlines()
                   if not l.lstrip().startswith('#')).replace(' ', '')
    if not body:
        return None
    return 'EMPTY' if body.rstrip(':,;') == '[1]' else 'NONEMPTY?!'


def run_cell(job):
    B, d, degP, degQ, corner = job
    tag = f'JC2D_B{B}_S{d}_{degP}_{degQ}_{corner}'
    t0 = time.time()
    try:
        fin, fout = f'cell_{tag}.ms', f'cell_{tag}.out'
        cached = parse_out(fout)
        if cached is not None:
            return f'{tag}: {cached} [cached]'
        eqs, vars_ = cell_system(d, degP, degQ, corner, sym='dihedral')
        open(fin, 'w').write(to_msolve(eqs, vars_))
        r = subprocess.run(['msolve', '-g', '2', '-t', '2', '-f', fin, '-o', fout],
                           capture_output=True, text=True, timeout=48*3600)
        verdict = parse_out(fout) or 'FAILED_NO_OUTPUT'
        return f'{tag}: {verdict} [{len(vars_)} vars, {len(eqs)} eqs, {time.time()-t0:.0f}s]'
    except Exception as ex:
        return f'{tag}: FAILED {type(ex).__name__}: {str(ex)[:120]} [{time.time()-t0:.0f}s]'


def main():
    jobs = []
    for B in range(BMIN, BMAX + 1):
        for d in range(3, B + 1):
            for (a, b) in ((2*B, 3*B), (3*B, 2*B)):
                for corner in ('extreme', 'w0'):
                    jobs.append((B, d, a, b, corner))
    # cheap first: low B, then large d (fewest weight lines)
    jobs.sort(key=lambda j: (j[0], -j[1]))
    print(f'{len(jobs)} dihedral JC2 cells, B={BMIN}..{BMAX}, {NCORES} workers',
          flush=True)
    # maxtasksperchild: recycle workers to bound sympy cache growth
    with mp.Pool(min(NCORES, len(jobs)), maxtasksperchild=2) as pool:
        with open('jc2_sym_results.log', 'a') as f:
            for line in pool.imap_unordered(run_cell, jobs):
                print(line, flush=True)
                f.write(line + '\n')
                f.flush()
                if 'NONEMPTY' in line:
                    print('!!! POTENTIAL JC_2 COUNTEREXAMPLE CELL !!!', flush=True)
    print('jc2 dihedral fleet complete', flush=True)


if __name__ == '__main__':
    main()
