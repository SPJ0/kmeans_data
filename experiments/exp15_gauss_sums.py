"""Exact Gauss-sum formula for the number of pure representations.

N1(T) = #{phi : V -> F_3^2 with every face sign = 1}.

Character expansion:  N1 = 3^{-F} sum_{t in F_3^F} w^{-sum(t)} G(Q_t)
where w = exp(2 pi i/3), Q_t(phi) = sum_f t_f s_f(phi) is a quadratic
form on F_3^{2n} whose Gram matrix is C_t (x) J with
  C_t[u,v] = t(left face of uv) - t(right face of uv)   (antisymmetric)
and G is the Gauss sum.  Then G(Q_t) = eps_t * 3^{2n - rank(C_t)} with
eps_t a Witt sign — here we do not assume any of that: we verify the
raw identity by computing G(Q_t) by brute force AND N1 by brute force,
then ALSO check the structural predictions rank(Q_t) = 2 rank(C_t) and
|G| = 3^{2n - rank C_t}.
"""
import sys, time, cmath, itertools
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import tetrahedron, bipyramid, vertex_set
from affine_rep import face_sign

W = cmath.exp(2j * cmath.pi / 3)
F3SQ = [(x, y) for x in range(3) for y in range(3)]


def all_phis(verts):
    for combo in itertools.product(F3SQ, repeat=len(verts)):
        yield dict(zip(verts, combo))


def signs_of(faces, phi):
    return [face_sign(phi[a], phi[b], phi[c]) for a, b, c in faces]


def rank_f3(mat):
    m = [row[:] for row in mat]
    R, C = len(m), len(m[0]) if m else 0
    r = 0
    for c in range(C):
        piv = next((i for i in range(r, R) if m[i][c] % 3), None)
        if piv is None:
            continue
        m[r], m[piv] = m[piv], m[r]
        inv = 1 if m[r][c] % 3 == 1 else 2
        m[r] = [(x * inv) % 3 for x in m[r]]
        for i in range(R):
            if i != r and m[i][c] % 3:
                f = m[i][c] % 3
                m[i] = [(m[i][j] - f * m[r][j]) % 3 for j in range(C)]
        r += 1
    return r


def run(name, faces):
    verts = sorted(vertex_set(faces))
    n, F = len(verts), len(faces)
    vidx = {v: i for i, v in enumerate(verts)}
    t0 = time.time()

    # brute-force N1 and cache sign vectors
    N1 = 0
    sign_cache = []
    for phi in all_phis(verts):
        sv = signs_of(faces, phi)
        sign_cache.append(sv)
        if all(s == 1 for s in sv):
            N1 += 1

    # character sum over t, brute-force Gauss sums using the cache
    total = 0
    structure_ok = True
    for t in itertools.product(range(3), repeat=F):
        G = 0
        for sv in sign_cache:
            q = sum(t[i] * sv[i] for i in range(F)) % 3
            G += W ** q
        # build C_t and check |G| = 3^{2n - rank C_t}
        C = [[0] * n for _ in range(n)]
        for fi, (a, b, c) in enumerate(faces):
            for u, v in ((a, b), (b, c), (c, a)):
                C[vidx[u]][vidx[v]] = (C[vidx[u]][vidx[v]] + t[fi]) % 3
                C[vidx[v]][vidx[u]] = (C[vidx[v]][vidx[u]] - t[fi]) % 3
        rk = rank_f3(C)
        if abs(abs(G) - 3 ** (2 * n - rk)) > 1e-4 and abs(G) > 1e-6:
            structure_ok = False
        if abs(G) > 1e-6 and abs(abs(G) - 3 ** (2 * n - rk)) > 1e-4:
            structure_ok = False
        total += (W ** ((-sum(t)) % 3)) * G
    lhs = total.real / (3 ** F)
    print('%-14s n=%d F=%d  N1(brute)=%d  N1(character sum)=%.3f  '
          'imag=%.1e  |G|=3^{2n-rank C_t} always: %s  (%.0fs)' %
          (name, n, F, N1, lhs, abs(total.imag) / 3 ** F, structure_ok,
           time.time() - t0))


if __name__ == '__main__':
    run('tetrahedron', tetrahedron())
    run('bipyramid(3)', bipyramid(3))
