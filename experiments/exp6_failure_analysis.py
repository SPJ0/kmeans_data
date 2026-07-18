"""Dissect extension failures and test stronger induction schemes:

  (i)  per-triangulation: does SOME contraction site (v,u) admit an
       extension from SOME representation of the contracted map?
  (ii) star repair: extend while allowed to re-color v AND its ring
       (colors outside the closed star stay fixed).
"""
import sys, time, itertools
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (random_triangulation, degrees, vertex_set,
                            adjacency, contractible_neighbors, contract,
                            check_triangulation, edge_faces)
from affine_rep import solve_affine, verify_affine, F3SQ, face_sign

CAP = 3000


def extend_p(faces, v, colors):
    for p in F3SQ:
        phi = dict(colors); phi[v] = p
        if verify_affine(faces, phi)[0]:
            return p
    return None


def star_repair(faces, v, colors):
    """Try re-coloring v and its ring, all else fixed."""
    ring = sorted(adjacency(faces)[v])
    others = {t: c for t, c in colors.items() if t not in ring}
    # backtracking over ring + v with full verification at the end
    # (small: |ring| <= 6 here); prune with pairwise adjacency distinctness
    adj = adjacency(faces)
    order = ring + [v]
    phi = dict(others)

    def bt(k):
        if k == len(order):
            return verify_affine(faces, phi)[0]
        t = order[k]
        for p in F3SQ:
            if any(u in phi and phi[u] == p for u in adj[t]):
                continue
            phi[t] = p
            if bt(k + 1):
                return True
            del phi[t]
        return False

    return bt(0)


def run(trials, sizes, seed0):
    tri_ok = tri_tot = 0
    edge_fail_details = []
    repair_fail = 0
    repair_cases = 0
    for trial in range(trials):
        n = sizes[trial % len(sizes)]
        faces = random_triangulation(n, seed=seed0 + trial)
        deg = degrees(faces)
        vs = sorted(deg, key=lambda x: deg[x])[:3]   # few low-degree sites
        any_site = False
        for v in vs:
            for u in contractible_neighbors(faces, v):
                fc = contract(faces, v, u)
                try:
                    check_triangulation(fc)
                except AssertionError:
                    continue
                sols = solve_affine(fc, all_solutions=True,
                                    max_solutions=CAP)
                ext = None
                for phi, _ in sols:
                    ext = extend_p(faces, v, phi)
                    if ext is not None:
                        break
                if ext is not None:
                    any_site = True
                else:
                    # try star repair on first few reps
                    repair_cases += 1
                    fixed = False
                    for phi, _ in sols[:40]:
                        if star_repair(faces, v, phi):
                            fixed = True
                            break
                    if fixed:
                        any_site = True
                    else:
                        repair_fail += 1
                        edge_fail_details.append(
                            (n, seed0 + trial, v, u, deg[v], len(sols)))
            if any_site:
                break
        tri_tot += 1
        tri_ok += any_site
    print('triangulations where SOME site extends (with repair fallback): '
          '%d/%d' % (tri_ok, tri_tot))
    print('plain-extension failures needing repair: %d; repair failed: %d'
          % (repair_cases, repair_fail))
    for d in edge_fail_details[:8]:
        print('  HARD:', d)


if __name__ == '__main__':
    t0 = time.time()
    run(80, [8, 9, 10, 11, 12, 13, 14, 16], seed0=9000)
    print('%.0fs' % (time.time() - t0))
