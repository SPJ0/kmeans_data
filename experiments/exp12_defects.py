"""Defect landscape of slope fields.

(a) Verify: total parity defect is always even (proved by the corner
    identity; sanity-checked here), on enumerated fields incl. invalid.
(b) Tait start: compute a proper 3-edge-coloring of the dual (colors =
    3 finite slopes, every face rainbow), examine the sign field it
    induces (sign mismatches on dual edges are defects), then run a
    local search over per-edge slope changes (4 slopes) minimizing
      #sign-defects + #parity-defects  (fold-adjacency violations count
    as sign defects) to try to reach a fully valid slope field.
"""
import sys, time, random
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (octahedron, icosahedron, bipyramid,
                            random_triangulation, undirected_edges,
                            vertex_set, adjacency, edge_faces)
from exp10_lifting import (SLOPES, REP, face_lambda_solutions,
                           face_sign_from_slopes, solvable_f2)


def build(faces):
    edges = undirected_edges(faces)
    eidx = {frozenset(e): i for i, e in enumerate(edges)}
    fedges, fdirs = [], []
    for (a, b, c) in faces:
        fedges.append([eidx[frozenset((a, b))], eidx[frozenset((b, c))],
                       eidx[frozenset((c, a))]])
        fdirs.append([0 if u < v else 1
                      for u, v in ((a, b), (b, c), (c, a))])
    owner = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)):
            owner[e] = i
    dual = [(owner[(a, b)], owner[(b, a)], eidx[frozenset((a, b))])
            for a, b in edges]
    # corners at each vertex: list of (face, local edge indices i1,i2)
    vcorners = {v: [] for v in vertex_set(faces)}
    for fi, (a, b, c) in enumerate(faces):
        trip = (a, b, c)
        for k, v in enumerate(trip):
            # boundary edges at v within this face: edges k-1 and k... the
            # edges (prev->v) and (v->next): local indices (k-1)%3 and k
            vcorners[v].append((fi, (k - 1) % 3, k))
    return edges, fedges, fdirs, dual, vcorners


def field_state(sigma, fedges, fdirs, dual, vcorners):
    """Return (sign_defects, parity_defects, valid_faces) for slope field."""
    nf = len(fedges)
    fsign = [None] * nf
    fbase = [None] * nf
    bad_faces = 0
    for fi in range(nf):
        sl = tuple(sigma[e] for e in fedges[fi])
        s = face_sign_from_slopes(sl)
        if s is None:
            bad_faces += 1
            continue
        fsign[fi] = s
        fbase[fi] = tuple(
            0 if l == 1 else 1 for l in face_lambda_solutions(sl)[0])
    sign_def = 0
    for fi, fj, e in dual:
        if fsign[fi] is None or fsign[fj] is None:
            sign_def += 1
        elif (fsign[fi] + fsign[fj]) % 3 == 0:
            sign_def += 1
    par_def = 0
    parities = {}
    for v, corners in vcorners.items():
        tot = 0
        okv = True
        for fi, i1, i2 in corners:
            if fbase[fi] is None:
                okv = False
                break
            b = fbase[fi]
            d = fdirs[fi]
            tot ^= b[i1] ^ b[i2] ^ d[i1] ^ d[i2]
        if not okv:
            tot = 1
        parities[v] = tot
        par_def += tot
    return bad_faces, sign_def, par_def, parities


def tait_coloring(faces, fedges, seed=0):
    """3-edge-coloring of the dual = slope assignment with every face
    rainbow in slopes {0,1,2}; backtracking."""
    E = max(max(fe) for fe in fedges) + 1
    sigma = [None] * E
    face_of_edge = {}
    for fi, fe in enumerate(fedges):
        for e in fe:
            face_of_edge.setdefault(e, []).append(fi)
    order = list(range(E))
    rng = random.Random(seed)
    rng.shuffle(order)

    def ok(e):
        for fi in face_of_edge[e]:
            sl = [sigma[x] for x in fedges[fi]]
            known = [s for s in sl if s is not None]
            if len(known) != len(set(known)):
                return False
        return True

    def bt(k):
        if k == E:
            return True
        e = order[k]
        for s in (0, 1, 2):
            sigma[e] = s
            if ok(e) and bt(k + 1):
                return True
        sigma[e] = None
        return False

    return sigma if bt(0) else None


def local_search(sigma, fedges, fdirs, dual, vcorners, steps=20000,
                 seed=0):
    rng = random.Random(seed)
    E = len(sigma)
    def cost(sg):
        bf, sd, pd, _ = field_state(sg, fedges, fdirs, dual, vcorners)
        return 100 * bf + 3 * sd + pd
    c = cost(sigma)
    for it in range(steps):
        if c == 0:
            return sigma, it
        e = rng.randrange(E)
        old = sigma[e]
        best_s, best_c = old, c
        cands = [s for s in SLOPES if s != old]
        rng.shuffle(cands)
        for s in cands:
            sigma[e] = s
            nc = cost(sigma)
            if nc < best_c or (nc == best_c and rng.random() < 0.25):
                best_s, best_c = s, nc
        sigma[e] = best_s
        c = best_c
        if rng.random() < 0.02:      # kick
            e2 = rng.randrange(E)
            sigma[e2] = rng.choice(SLOPES)
            c = cost(sigma)
    return (sigma, None) if c != 0 else (sigma, steps)


if __name__ == '__main__':
    cases = [('octahedron', octahedron()),
             ('icosahedron', icosahedron()),
             ('bipyramid(6)', bipyramid(6))]
    for s in range(3):
        cases.append(('random(n=16,s=%d)' % s,
                      random_triangulation(16, seed=s)))
        cases.append(('random(n=24,s=%d)' % s,
                      random_triangulation(24, seed=s + 50)))
    for name, faces in cases:
        edges, fedges, fdirs, dual, vcorners = build(faces)
        t = tait_coloring(faces, fedges)
        if t is None:
            print('%-18s NO TAIT COLORING FOUND' % name)
            continue
        bf, sd, pd, par = field_state(t, fedges, fdirs, dual, vcorners)
        assert bf == 0
        assert pd % 2 == 0, 'odd total parity defect!'
        t0 = time.time()
        res, iters = local_search(list(t), fedges, fdirs, dual, vcorners,
                                  seed=1)
        bf2, sd2, pd2, _ = field_state(res, fedges, fdirs, dual, vcorners)
        done = (bf2 == 0 and sd2 == 0 and pd2 == 0)
        print('%-18s tait: sign-defects=%2d parity-defects=%2d -> '
              'local search: %s (iters=%s, %.1fs)' %
              (name, sd, pd, 'VALID FIELD' if done else
               'stuck(bf=%d sd=%d pd=%d)' % (bf2, sd2, pd2),
               iters, time.time() - t0))
