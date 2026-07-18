import sys, time, json
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (random_triangulation, check_triangulation,
                            vertex_set, degrees)
from diagonal import diagonal_chromatic_number
from affine_rep import solve_affine, verify_affine

OUT = __file__.rsplit('/', 2)[0] + '/experiments/hard_instances.json'

def hunt(trials, sizes, seed0):
    found = []
    for trial in range(trials):
        n = sizes[trial % len(sizes)]
        faces = random_triangulation(n, seed=seed0 + trial)
        chi, _ = diagonal_chromatic_number(faces)
        if chi is not None and chi >= 8:
            found.append((chi, n, seed0 + trial, faces))
    return found

if __name__ == '__main__':
    t0 = time.time()
    found = hunt(1200, [9, 10, 11, 12, 13], seed0=1000)
    found += hunt(500, [15, 17, 19], seed0=50000)
    print('hunt took %.1fs, found %d instances with chi>=8' %
          (time.time() - t0, len(found)))
    hard = []
    for chi, n, seed, faces in sorted(found, key=lambda t: -t[0]):
        phi, signs = solve_affine(faces)
        ok = False
        if phi is not None:
            ok, msg = verify_affine(faces, phi)
        zero = sum(1 for s in signs.values() if s == 0) if signs else -1
        print('chi=%d n=%2d seed=%6d affine=%s zero=%d' %
              (chi, n, seed, ok, zero))
        hard.append({'chi': chi, 'n': n, 'seed': seed,
                     'faces': [list(f) for f in faces], 'affine': bool(ok)})
    with open(OUT, 'w') as fh:
        json.dump(hard, fh)
    nine = [h for h in hard if h['chi'] == 9]
    print('chi=9 instances: %d, all affine: %s' %
          (len(nine), all(h['affine'] for h in nine)))
    print('all chi>=8 affine: %s' % all(h['affine'] for h in hard))
