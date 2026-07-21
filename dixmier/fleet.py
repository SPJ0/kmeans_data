"""Fleet driver: close every sublattice cell of the B=16 Dixmier layer with msolve.

Each cell = (d, degP, degQ, corner): canonical pairs [Q,P]=1 supported in S_d
with Bernstein caps, corner-type saturation. Verdict per cell:
  EMPTY    -> cell provably contains no Dixmier pair (over GF(p) for the primes
              used by msolve's -g 2 run over Q: we run exact, so it's a theorem)
  NONEMPTY -> candidate counterexample to DC_1: STOP EVERYTHING and lift it.
"""
import sys, os, time, subprocess, multiprocessing as mp
import sympy as sp
from cascade2 import cell_system

NCORES = int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()
B = int(sys.argv[2]) if len(sys.argv) > 2 else 16  # layer: bidegrees (2B, 3B)

def to_msolve(eqs, vars_):
    lines = [','.join(str(v) for v in vars_), '0']
    body = []
    for e in eqs:
        s = str(sp.expand(e)).replace('**', '^').replace(' ', '')
        body.append(s)
    return '\n'.join(lines) + '\n' + ',\n'.join(body) + '\n'

def run_cell(job):
    d, degP, degQ, corner = job
    tag = f'S{d}_{degP}_{degQ}_{corner}'
    t0 = time.time()
    try:
        eqs, vars_ = cell_system(d, degP, degQ, corner)
        ms = to_msolve(eqs, vars_)
        fin, fout = f'cell_{tag}.ms', f'cell_{tag}.out'
        open(fin, 'w').write(ms)
        # -g 2: reduced Groebner basis, grevlex; exact over Q
        r = subprocess.run(['msolve', '-g', '2', '-t', '2', '-f', fin, '-o', fout],
                           capture_output=True, text=True, timeout=48*3600)
        out = open(fout).read() if os.path.exists(fout) else ''
        # msolve prepends '#' comment headers and may split the basis across
        # lines ('[1\n]:'), so strip comments before flattening.
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
    # layer B: all sublattice steps, both Bernstein orientations, both corners.
    for d in range(2, B + 1):
        for (a, b) in ((2*B, 3*B), (3*B, 2*B)):
            for corner in ('extreme', 'w0'):
                jobs.append((d, a, b, corner))
    # smallest systems first (largest d): fast wins early
    jobs.sort(key=lambda j: (-j[0], j[1]))
    print(f'{len(jobs)} cells (layer B={B}), {NCORES} workers', flush=True)
    with mp.Pool(min(NCORES, len(jobs))) as pool:
        with open('results.log', 'a') as f:
            for line in pool.imap_unordered(run_cell, jobs):
                print(line, flush=True)
                f.write(line + '\n'); f.flush()
                if 'NONEMPTY' in line:
                    print('!!! POTENTIAL COUNTEREXAMPLE CELL — preserve .ms/.out files !!!', flush=True)
    print('fleet complete', flush=True)

if __name__ == '__main__':
    main()
