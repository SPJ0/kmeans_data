"""Lifting theory for slope fields.

A slope field assigns sigma(e) in PG(1,3) = {0,1,2,inf} to each edge.
Face-local validity (for ccw face with boundary edges e1,e2,e3):
  * rainbow: three distinct slopes, or
  * mono: equal slopes (fold face; must be independent in the dual and
    is then constrained to lambda1=lambda2=lambda3).
Lifting: z(e) = lambda(e) * w(sigma(e)), lambda(e) in {+1,-1}, subject
to closedness z1+z2+z3 = 0 per face.  In mu-coordinates
(lambda = (-1)^mu) each face imposes two F_2-linear equations pinning
pairwise sums of its three mu's; the sign of a rainbow face is
determined by slopes alone (verified in exp9).

This experiment: enumerate valid slope fields on small triangulations
(face-local + fold-independence + adjacent slope-determined signs not
opposite), build the F_2 system, test solvability, and compare with the
vertex parity condition sum of a_i around each vertex = 0, where
mu(e_i)+mu(e_{i+1}) = a_i comes from the face between spokes e_i,e_{i+1}.
"""
import sys, time
from itertools import product
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (octahedron, bipyramid, random_triangulation,
                            undirected_edges, edge_faces, vertex_set,
                            adjacency)
from affine_rep import det

SLOPES = [0, 1, 2, 'inf']
REP = {0: (1, 0), 1: (1, 1), 2: (1, 2), 'inf': (0, 1)}


def neg(w):
    return ((-w[0]) % 3, (-w[1]) % 3)


def face_lambda_solutions(slopes3):
    """All (l1,l2,l3) in {1,2}^3 with sum of l_i * w(slope_i) = 0."""
    w = [REP[s] for s in slopes3]
    sols = []
    for ls in product((1, 2), repeat=3):
        sx = sum(ls[i] * w[i][0] for i in range(3)) % 3
        sy = sum(ls[i] * w[i][1] for i in range(3)) % 3
        if sx == 0 and sy == 0:
            sols.append(ls)
    return sols


def face_sign_from_slopes(slopes3):
    """Sign of a face given the cyclic slope sequence (rainbow), or 0
    (mono).  None if the slope triple is invalid."""
    if len(set(slopes3)) == 1:
        return 0
    if len(set(slopes3)) != 3:
        return None
    sols = face_lambda_solutions(slopes3)
    if not sols:
        return None
    prods = {(l1 * l2) % 3 for l1, l2, l3 in sols}
    assert len(prods) == 1
    return (prods.pop() * det(REP[slopes3[0]], REP[slopes3[1]])) % 3


def solvable_f2(eqs, nvars):
    """Gaussian elimination over F_2; eqs: list of (bitmask, rhs)."""
    rows = [(m, r) for m, r in eqs]
    pivots = {}
    for m, r in rows:
        cur, rhs = m, r
        while cur:
            b = cur & -cur
            if b in pivots:
                pm, pr = pivots[b]
                cur ^= pm
                rhs ^= pr
            else:
                pivots[b] = (cur, rhs)
                cur = 0
                rhs = None
        if cur == 0 and rhs == 1:
            return False
    return True


def analyze(faces, cap_fields=4000):
    edges = undirected_edges(faces)
    eidx = {frozenset(e): i for i, e in enumerate(edges)}
    E = len(edges)
    third = edge_faces(faces)
    # face adjacency with shared edge
    fedges = []          # per face: its 3 boundary edges (ccw order)
    fdirs = []           # 0 if traversal matches sorted reference, else 1
    for (a, b, c) in faces:
        fedges.append([frozenset((a, b)), frozenset((b, c)),
                       frozenset((c, a))])
        fdirs.append([0 if u < v else 1
                      for u, v in ((a, b), (b, c), (c, a))])
    dual_adj = []        # (face_i, face_j) sharing an edge
    owner = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)):
            owner[e] = i
    for a, b in edges:
        dual_adj.append((owner[(a, b)], owner[(b, a)]))

    stats = {'fields': 0, 'liftable': 0, 'parity_ok': 0, 'agree': 0}

    # backtracking over edge slopes, face-checked when complete
    order = list(range(E))
    sigma = [None] * E

    def face_complete_check(fi):
        sl = tuple(sigma[eidx[e]] for e in fedges[fi])
        if any(s is None for s in sl):
            return True, None
        s = face_sign_from_slopes(sl)
        if s is None:
            return False, None
        return True, s

    fsign = [None] * len(faces)

    results = []

    def bt(k):
        if stats['fields'] >= cap_fields:
            return
        if k == E:
            # fold independence + sign adjacency
            for i, j in dual_adj:
                si, sj = fsign[i], fsign[j]
                if (si + sj) % 3 == 0:
                    return
            stats['fields'] += 1
            # build F_2 system
            eqs = []
            for fi, fe in enumerate(fedges):
                sl = tuple(sigma[eidx[e]] for e in fe)
                sols = face_lambda_solutions(sl)
                if not sols:
                    return
                base = tuple(0 if l == 1 else 1 for l in sols[0])
                d = fdirs[fi]
                ids = [eidx[e] for e in fe]
                eqs.append(((1 << ids[0]) | (1 << ids[1]),
                            base[0] ^ base[1] ^ d[0] ^ d[1]))
                eqs.append(((1 << ids[1]) | (1 << ids[2]),
                            base[1] ^ base[2] ^ d[1] ^ d[2]))
            lift = solvable_f2(eqs, E)
            # vertex parity: around v, spokes e_i; face between spokes
            # contributes a_i = pinned mu(e_i)+mu(e_{i+1})
            parity_ok = True
            adj = adjacency(faces)
            for v in vertex_set(faces):
                tot = 0
                # walk faces around v
                for u in adj[v]:
                    w = third[(v, u)]     # face (v,u,w): spokes vu, vw
                    sl_face = None
                    for fi, (a, b, c) in enumerate(faces):
                        if {a, b, c} == {v, u, w}:
                            sl_face = fi
                            break
                    fe = fedges[sl_face]
                    sl = tuple(sigma[eidx[e]] for e in fe)
                    sols = face_lambda_solutions(sl)
                    base = tuple(0 if l == 1 else 1 for l in sols[0])
                    d = fdirs[sl_face]
                    i1 = fe.index(frozenset((v, u)))
                    i2 = fe.index(frozenset((v, w)))
                    tot ^= base[i1] ^ base[i2] ^ d[i1] ^ d[i2]
                if tot != 0:
                    parity_ok = False
                    break
            stats['liftable'] += lift
            stats['parity_ok'] += parity_ok
            stats['agree'] += (lift == parity_ok)
            results.append((lift, parity_ok))
            return
        # try slopes for edge k with partial face pruning
        for s in SLOPES:
            sigma[k] = s
            ok = True
            for fi, fe in enumerate(fedges):
                if eidx.get(frozenset(edges[k])) is not None and \
                        frozenset(edges[k]) in fe:
                    good, sg = face_complete_check(fi)
                    if not good:
                        ok = False
                        break
                    if sg is not None:
                        fsign[fi] = sg
            if ok:
                bt(k + 1)
            for fi, fe in enumerate(fedges):
                if frozenset(edges[k]) in fe:
                    sl = tuple(sigma[eidx[e]] for e in fe)
                    if any(x is None for x in sl):
                        fsign[fi] = None
            sigma[k] = None
        return

    bt(0)
    return stats


if __name__ == '__main__':
    t0 = time.time()
    for name, faces in [('bipyramid(3)', bipyramid(3)),
                        ('octahedron', octahedron())]:
        st = analyze(faces)
        print('%-14s fields=%d liftable=%d parity_ok=%d agree=%d/%d [%.0fs]'
              % (name, st['fields'], st['liftable'], st['parity_ok'],
                 st['agree'], st['fields'], time.time() - t0))
