"""Fleet driver for the planar (JC_2) B=16 layer — commutative analog of fleet.py.

Each cell = (d, degP, degQ, corner) from jc2_cascade.cell_system. Verdict per
cell via msolve reduced Groebner basis over Q:
  EMPTY    -> no S_d-supported Jacobian pair under the caps (theorem)
  NONEMPTY -> candidate counterexample to JC_2: STOP EVERYTHING and lift it.
"""
import multiprocessing as mp
import os
import subprocess
import sys
import time

import sympy as sp

from jc2_cascade import cell_system

NCORES = int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()
B = int(sys.argv[2]) if len(sys.argv) > 2 else 16  # layer: bidegrees (2B, 3B)


def to_msolve(eqs, vars_):
    lines = [','.join(str(v) for v in vars_), '0']
    body = [str(sp.expand(e)).replace('**', '^').replace(' ', '') for e in eqs]
    return '\n'.join(lines) + '\n' + ',\n'.join(body) + '\n'


def run_cell(job):
    d, degP, degQ, corner = job
    tag = f'JC2_S{d}_{degP}_{degQ}_{corner}'
    t0 = time.time()
    try:
        eqs, vars_ = cell_system(d, degP, degQ, corner)
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
    for d in range(2, B + 1):
        for (a, b) in ((2*B, 3*B), (3*B, 2*B)):
            for corner in ('extreme', 'w0'):
                jobs.append((d, a, b, corner))
    jobs.sort(key=lambda j: (-j[0], j[1]))
    print(f'{len(jobs)} JC2 cells (layer B={B}), {NCORES} workers', flush=True)
    with mp.Pool(min(NCORES, len(jobs))) as pool:
        with open('jc2_results.log', 'a') as f:
            for line in pool.imap_unordered(run_cell, jobs):
                print(line, flush=True)
                f.write(line + '\n')
                f.flush()
                if 'NONEMPTY' in line:
                    print('!!! POTENTIAL JC_2 COUNTEREXAMPLE CELL !!!', flush=True)
    print('jc2 fleet complete', flush=True)


if __name__ == '__main__':
    main()
