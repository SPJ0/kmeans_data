import sys, time
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (tetrahedron, octahedron, icosahedron, bipyramid,
                            random_stacked, random_triangulation,
                            check_triangulation, vertex_set, degrees)
from diagonal import diagonal_chromatic_number, diagonal_graph
from affine_rep import solve_affine, verify_affine


def report(name, faces):
    check_triangulation(faces)
    n = len(vertex_set(faces))
    F = len(faces)
    chi, _ = diagonal_chromatic_number(faces)
    t0 = time.time()
    phi, signs = solve_affine(faces)
    dt = time.time() - t0
    aff = 'none'
    if phi is not None:
        ok, msg = verify_affine(faces, phi)
        ncolors = len(set(phi.values()))
        zero = sum(1 for s in signs.values() if s == 0)
        aff = 'YES(%s, colors=%d, zero-faces=%d)' % (msg, ncolors, zero)
    print('%-22s n=%3d F=%3d F%%3=%d chi_diag=%2s affine=%s (%.2fs)' %
          (name, n, F, F % 3, chi, aff, dt))
    return phi is not None


if __name__ == '__main__':
    report('tetrahedron', tetrahedron())
    report('octahedron', octahedron())
    report('icosahedron', icosahedron())
    for m in range(3, 9):
        report('bipyramid(%d)' % m, bipyramid(m))
    for seed in range(3):
        report('stacked(n=12,s=%d)' % seed, random_stacked(12, seed=seed))
    for seed in range(3):
        report('random(n=14,s=%d)' % seed,
               random_triangulation(14, seed=seed))
    for seed in range(3):
        report('random(n=20,s=%d)' % seed,
               random_triangulation(20, seed=seed))
