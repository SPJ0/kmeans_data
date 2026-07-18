import sys, time
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (bipyramid, random_stacked, random_triangulation,
                            check_triangulation, vertex_set, degrees)
from diagonal import diagonal_chromatic_number, diagonal_graph, color_graph
from affine_rep import solve_affine, verify_affine

def pure_test():
    print('--- pure det=1 (only possible if F %% 3 == 0, i.e. n %% 3 == 2) ---')
    cases = [('bipyramid(3)', bipyramid(3)), ('bipyramid(6)', bipyramid(6)),
             ('bipyramid(9)', bipyramid(9)), ('bipyramid(12)', bipyramid(12))]
    for seed in range(6):
        for n in (14, 17, 20, 23):
            cases.append(('random(n=%d,s=%d)' % (n, seed),
                          random_triangulation(n, seed=seed)))
    for name, faces in cases:
        F = len(faces)
        if F % 3 != 0:
            continue
        t0 = time.time()
        phi, signs = solve_affine(faces, pure_sign=1)
        dt = time.time() - t0
        res = 'PURE-YES' if phi is not None else 'PURE-NO'
        if phi is not None:
            ok, msg = verify_affine(faces, phi)
            assert ok, msg
        print('%-22s F=%3d %s (%.2fs)' % (name, F, res, dt))

def scale_test():
    print('--- larger random triangulations, affine with zero faces ---')
    for seed in range(4):
        for n in (30, 40, 50):
            faces = random_triangulation(n, seed=seed)
            check_triangulation(faces)
            mind = min(degrees(faces).values())
            t0 = time.time()
            phi, signs = solve_affine(faces)
            dt = time.time() - t0
            status = 'none'
            if phi is not None:
                ok, msg = verify_affine(faces, phi)
                zero = sum(1 for s in signs.values() if s == 0)
                status = 'YES(%s, zero=%d/%d)' % (msg, zero, len(faces))
            # is it 9-diagonal-colorable at all?
            nine = color_graph(diagonal_graph(faces), 9) is not None
            print('n=%3d s=%d mindeg=%d 9col=%s affine=%s (%.2fs)' %
                  (n, seed, mind, nine, status, dt))

def hard_hunt():
    print('--- hunting for chi_diag >= 8 instances ---')
    best = {}
    import random as _r
    for trial in range(400):
        rng = _r.Random(trial)
        n = rng.choice([9, 10, 11, 12, 13, 14])
        faces = random_triangulation(n, seed=trial + 1000)
        chi, _ = diagonal_chromatic_number(faces)
        if chi is not None and chi >= 8:
            print('trial=%d n=%d chi=%d degs=%s' %
                  (trial, n, chi, sorted(degrees(faces).values())))
            best[chi] = faces
    if not best:
        print('none found with chi >= 8 in this sweep')
    return best

if __name__ == '__main__':
    pure_test()
    scale_test()
    hard_hunt()
