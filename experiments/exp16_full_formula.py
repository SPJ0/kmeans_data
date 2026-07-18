"""Theorem 9: exact lattice-sum formula for the number of affine
representations (fold-allowing), verified brute-force.

N_valid = #{phi : z(e) != 0 on all edges, s_f + s_g != 0 on all dual
edges}  (exactly the affine representations, by the shape
classification).

Formula:
  N_valid = sum_{S subset E} (-1)^{|S|}
            sum_{c in F_3^D} (2/3)^{z(c)} (-1/3)^{|D|-z(c)}
            3^{2 comp(S) - rank Cbar_{dc}(S)}
where D = dual edges, t = boundary(c) weights each face by the sum of
its dual-edge charges, comp(S) = # components of (V,S), and Cbar is
the t-difference matrix contracted along S.
"""
import sys, time, itertools
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import tetrahedron, vertex_set, undirected_edges
from affine_rep import face_sign
from exp15_gauss_sums import rank_f3, F3SQ, all_phis, signs_of


def brute_valid(faces):
    verts = sorted(vertex_set(faces))
    edges = undirected_edges(faces)
    # dual edges: pairs of faces sharing an edge
    owner = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)):
            owner[e] = i
    duals = [(owner[(u, v)], owner[(v, u)]) for u, v in edges]
    cnt = 0
    for phi in all_phis(verts):
        if any(phi[u] == phi[v] for u, v in edges):
            continue
        sv = signs_of(faces, phi)
        if all((sv[i] + sv[j]) % 3 != 0 for i, j in duals):
            cnt += 1
    return cnt


def formula_valid(faces):
    verts = sorted(vertex_set(faces))
    n = len(verts)
    vidx = {v: i for i, v in enumerate(verts)}
    edges = undirected_edges(faces)
    E = len(edges)
    owner = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)):
            owner[e] = i
    duals = [(owner[(u, v)], owner[(v, u)]) for u, v in edges]
    D = len(duals)
    F = len(faces)

    total = 0.0
    for c in itertools.product(range(3), repeat=D):
        t = [0] * F
        for di, (fi, fj) in enumerate(duals):
            t[fi] = (t[fi] + c[di]) % 3
            t[fj] = (t[fj] + c[di]) % 3
        zc = sum(1 for x in c if x == 0)
        wc = (2.0 / 3.0) ** zc * (-1.0 / 3.0) ** (D - zc)
        # C_t on the full vertex set
        C = [[0] * n for _ in range(n)]
        for fi, (a, b, cc) in enumerate(faces):
            for u, v in ((a, b), (b, cc), (cc, a)):
                C[vidx[u]][vidx[v]] = (C[vidx[u]][vidx[v]] + t[fi]) % 3
                C[vidx[v]][vidx[u]] = (C[vidx[v]][vidx[u]] - t[fi]) % 3
        acc_S = 0.0
        for smask in range(1 << E):
            # components of (V, S)
            parent = list(range(n))
            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            bits = 0
            for ei in range(E):
                if smask >> ei & 1:
                    bits += 1
                    u, v = edges[ei]
                    ru, rv = find(vidx[u]), find(vidx[v])
                    if ru != rv:
                        parent[ru] = rv
            comps = {}
            for i in range(n):
                comps.setdefault(find(i), len(comps))
            k = len(comps)
            Cb = [[0] * k for _ in range(k)]
            for i in range(n):
                for j in range(n):
                    if C[i][j]:
                        a_, b_ = comps[find(i)], comps[find(j)]
                        Cb[a_][b_] = (Cb[a_][b_] + C[i][j]) % 3
            rk = rank_f3(Cb)
            acc_S += (-1) ** bits * 3.0 ** (2 * k - rk)
        total += wc * acc_S
    return total


if __name__ == '__main__':
    faces = tetrahedron()
    t0 = time.time()
    b = brute_valid(faces)
    f = formula_valid(faces)
    print('tetrahedron: brute N_valid=%d  formula=%.4f  (%.0fs)'
          % (b, f, time.time() - t0))
