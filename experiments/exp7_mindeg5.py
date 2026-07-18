"""1. Mechanically check the classical reduction: for a vertex v of
degree 3 or 4, deleting v (and adding a quad diagonal if deg 4) leaves a
triangulation T' such that EVERY diagonal 9-coloring of T' extends to T
(the forbidden-color count for v is at most 6 resp. 8).

2. Generate minimum-degree-5 triangulations (Loop subdivision of the
icosahedron + degree-preserving random flips, plus hill-climbed random
triangulations) and test affine representability — the class where the
Nine Conjecture now lives.
"""
import sys, time, random
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (icosahedron, random_triangulation, degrees,
                            vertex_set, adjacency, edge_faces, flip,
                            undirected_edges, check_triangulation)
from diagonal import diagonal_graph, color_graph, check_diagonal_coloring
from affine_rep import solve_affine, verify_affine


def forbidden_count(faces, v):
    """|colors forbidden for v| upper bound structure: neighbors plus
    opposite vertices across link edges."""
    third = edge_faces(faces)
    adj = adjacency(faces)
    ring = adj[v]
    opp = set()
    for u in ring:
        # link edges at v are edges (u, w) with faces (v,u,w); the
        # conflict partners of v across its star are thirds of outer faces
        pass
    conf = set()
    for u, w in undirected_edges(faces):
        a, b = third[(u, w)], third[(w, u)]
        if a == v:
            conf.add(b)
        if b == v:
            conf.add(a)
    conf |= ring
    conf.discard(v)
    return len(conf)


def reduction_check(trials=300, seed0=100):
    worst3 = worst4 = 0
    for t in range(trials):
        faces = random_triangulation(random.Random(t + seed0).choice(
            [8, 10, 12, 15, 20]), seed=t + seed0)
        deg = degrees(faces)
        for v, d in deg.items():
            if d == 3:
                worst3 = max(worst3, forbidden_count(faces, v))
            elif d == 4:
                worst4 = max(worst4, forbidden_count(faces, v))
    print('max #conflicts of a degree-3 vertex observed: %d (proof bound 6)'
          % worst3)
    print('max #conflicts of a degree-4 vertex observed: %d (proof bound 8)'
          % worst4)


def loop_subdivide(faces):
    verts = vertex_set(faces)
    nxt = max(verts) + 1
    mid = {}
    for u, v in undirected_edges(faces):
        mid[frozenset((u, v))] = nxt
        nxt += 1
    out = []
    for a, b, c in faces:
        ab = mid[frozenset((a, b))]
        bc = mid[frozenset((b, c))]
        ca = mid[frozenset((c, a))]
        out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    return out


def mindeg5_flips(faces, k, seed=None):
    rng = random.Random(seed)
    for _ in range(k):
        es = undirected_edges(faces)
        u, v = es[rng.randrange(len(es))]
        deg = degrees(faces)
        if deg[u] <= 5 or deg[v] <= 5:
            continue
        nf = flip(faces, u, v)
        if nf is not None and min(degrees(nf).values()) >= 5:
            faces = nf
    return faces


def hillclimb_mindeg5(n, seed=None, steps=4000):
    rng = random.Random(seed)
    faces = random_triangulation(n, seed=seed)

    def badness(fs):
        return sum(max(0, 5 - d) for d in degrees(fs).values())

    b = badness(faces)
    for _ in range(steps):
        if b == 0:
            return faces
        es = undirected_edges(faces)
        u, v = es[rng.randrange(len(es))]
        nf = flip(faces, u, v)
        if nf is None:
            continue
        nb = badness(nf)
        if nb <= b:
            faces, b = nf, nb
    return faces if b == 0 else None


def affine_report(name, faces):
    check_triangulation(faces)
    n = len(vertex_set(faces))
    mind = min(degrees(faces).values())
    t0 = time.time()
    phi, signs = solve_affine(faces)
    dt = time.time() - t0
    if phi is None:
        print('%-28s n=%4d mindeg=%d affine=NONE (%.1fs)' % (name, n, mind, dt))
        return False
    ok, msg = verify_affine(faces, phi)
    zero = sum(1 for s in signs.values() if s == 0)
    print('%-28s n=%4d mindeg=%d affine=%s zero=%d/%d (%.1fs)' %
          (name, n, mind, ok, zero, len(faces), dt))
    return ok


if __name__ == '__main__':
    reduction_check()
    print()
    ico = icosahedron()
    affine_report('icosahedron', ico)
    g2 = loop_subdivide(ico)
    affine_report('geodesic-2 (n=42)', g2)
    for s in range(4):
        affine_report('geodesic-2 + flips s=%d' % s,
                      mindeg5_flips(g2, 400, seed=s))
    g4 = loop_subdivide(g2)
    affine_report('geodesic-4 (n=162)', g4)
    affine_report('geodesic-4 + flips', mindeg5_flips(g4, 600, seed=1))
    print()
    found = 0
    for n in (13, 14, 15, 16, 17, 18, 19, 20, 24, 28):
        for s in range(8):
            f = hillclimb_mindeg5(n, seed=1000 * n + s)
            if f is not None:
                affine_report('hillclimb n=%d s=%d' % (n, s), f)
                found += 1
                break
        else:
            print('no min-deg-5 triangulation found at n=%d (may not exist)'
                  % n)
