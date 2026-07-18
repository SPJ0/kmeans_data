"""Test the extension lemma behind the contraction induction:

Given T and a min-degree vertex v, contract a contractible edge (v,u)
to get T'.  For representations phi' of T', ask whether phi' extends to
T by choosing only phi(v) = p in F_3^2 (all other colors kept).

Metrics per (T, u): does the solver's first representation extend?
does ANY of up to CAP enumerated representations extend?
"""
import sys, time
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (random_triangulation, degrees, vertex_set,
                            contractible_neighbors, contract,
                            check_triangulation)
from affine_rep import solve_affine, verify_affine, F3SQ

CAP = 3000


def extensions(faces, v, colors):
    """All p making colors + {v: p} an affine representation of faces."""
    good = []
    for p in F3SQ:
        phi = dict(colors)
        phi[v] = p
        ok, _ = verify_affine(faces, phi)
        if ok:
            good.append(p)
    return good


def run(trials, sizes, seed0):
    stats = {'cases': 0, 'first': 0, 'any': 0, 'reps_tried': 0}
    bad = []
    for trial in range(trials):
        n = sizes[trial % len(sizes)]
        faces = random_triangulation(n, seed=seed0 + trial)
        deg = degrees(faces)
        v = min(deg, key=lambda x: deg[x])
        for u in contractible_neighbors(faces, v):
            fc = contract(faces, v, u)
            try:
                check_triangulation(fc)
            except AssertionError:
                continue
            sols = solve_affine(fc, all_solutions=True, max_solutions=CAP)
            if not sols:
                bad.append(('NO-REP-OF-CONTRACTED', n, seed0 + trial, u))
                continue
            stats['cases'] += 1
            stats['reps_tried'] += len(sols)
            ext_first = bool(extensions(faces, v, sols[0][0]))
            ext_any = ext_first or any(
                extensions(faces, v, phi) for phi, _ in sols[1:])
            stats['first'] += ext_first
            stats['any'] += ext_any
            if not ext_any:
                bad.append(('NO-EXTENSION', n, seed0 + trial, u,
                            len(sols), deg[v]))
    return stats, bad


if __name__ == '__main__':
    t0 = time.time()
    stats, bad = run(60, [8, 9, 10, 11, 12, 14], seed0=7000)
    print('cases=%d  first-rep extends: %d (%.0f%%)  any rep extends: %d '
          '(%.0f%%)  avg reps enumerated: %.0f  (%.0fs)' %
          (stats['cases'], stats['first'],
           100.0 * stats['first'] / max(stats['cases'], 1),
           stats['any'], 100.0 * stats['any'] / max(stats['cases'], 1),
           stats['reps_tried'] / max(stats['cases'], 1), time.time() - t0))
    for b in bad[:10]:
        print('BAD:', b)
