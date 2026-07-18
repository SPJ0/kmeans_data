"""Sphere triangulations as sets of ccw-oriented faces.

A triangulation of the sphere is stored as a list of oriented triples
(a, b, c) meaning the face with ccw boundary a -> b -> c.  Consistency
invariant: every directed edge (u, v) appears in exactly one face.
"""

import random
from collections import defaultdict


def check_triangulation(faces):
    """Verify the oriented-face invariant and simplicity."""
    directed = {}
    for f in faces:
        a, b, c = f
        assert len({a, b, c}) == 3, f"degenerate face {f}"
        for u, v in ((a, b), (b, c), (c, a)):
            assert (u, v) not in directed, f"directed edge {(u,v)} twice"
            directed[(u, v)] = f
    for (u, v) in directed:
        assert (v, u) in directed, f"missing reverse of {(u,v)}"
    verts = vertex_set(faces)
    n, e, fc = len(verts), len(directed) // 2, len(faces)
    assert n - e + fc == 2, f"Euler failure n={n} e={e} f={fc}"
    assert fc == 2 * n - 4
    return True


def vertex_set(faces):
    s = set()
    for f in faces:
        s.update(f)
    return s


def edge_faces(faces):
    """Map directed edge (u,v) -> third vertex w of the face (u,v,w)."""
    third = {}
    for a, b, c in faces:
        third[(a, b)] = c
        third[(b, c)] = a
        third[(c, a)] = b
    return third


def undirected_edges(faces):
    es = set()
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            es.add(frozenset((u, v)))
    return [tuple(sorted(e)) for e in es]


def adjacency(faces):
    adj = defaultdict(set)
    for a, b, c in faces:
        adj[a].update((b, c))
        adj[b].update((a, c))
        adj[c].update((a, b))
    return adj


def degrees(faces):
    return {v: len(nb) for v, nb in adjacency(faces).items()}


# ---------------------------------------------------------------- builders

def tetrahedron():
    return [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]


def bipyramid(m):
    """Double pyramid over an m-cycle: n = m + 2 vertices."""
    a, b = m, m + 1
    faces = []
    for i in range(m):
        j = (i + 1) % m
        faces.append((a, i, j))
        faces.append((b, j, i))
    return faces


def octahedron():
    return bipyramid(4)


def icosahedron():
    top, bot = 10, 11
    up = list(range(5))          # upper pentagon
    dn = list(range(5, 10))      # lower pentagon
    faces = []
    for i in range(5):
        j = (i + 1) % 5
        faces.append((top, up[i], up[j]))
        faces.append((bot, dn[j], dn[i]))
        # antiprism belt between up and dn (dn[i] below edge up[i]..up[j])
        faces.append((up[i], dn[i], up[j]))
        faces.append((up[j], dn[i], dn[j]))
    return faces


def stack_vertex(faces, face_idx, new_v):
    """Subdivide face #face_idx with a new degree-3 vertex."""
    a, b, c = faces[face_idx]
    out = faces[:face_idx] + faces[face_idx + 1:]
    out += [(a, b, new_v), (b, c, new_v), (c, a, new_v)]
    return out


def random_stacked(n, seed=None):
    rng = random.Random(seed)
    faces = tetrahedron()
    for v in range(4, n):
        faces = stack_vertex(faces, rng.randrange(len(faces)), v)
    return faces


def flip(faces, u, v):
    """Flip diagonal uv of the quad around it.  Returns new faces or None."""
    third = edge_faces(faces)
    if (u, v) not in third or (v, u) not in third:
        return None
    w = third[(u, v)]   # face (u, v, w)
    x = third[(v, u)]   # face (v, u, x)
    if w == x:
        return None
    # new edge {w, x} must not already exist
    if (w, x) in third or (x, w) in third:
        return None
    fs = set(faces)
    fs.discard((u, v, w)); fs.discard((v, w, u)); fs.discard((w, u, v))
    fs.discard((v, u, x)); fs.discard((u, x, v)); fs.discard((x, v, u))
    fs.add((u, x, w))
    fs.add((x, v, w))
    return list(fs)


def random_flips(faces, k, seed=None):
    rng = random.Random(seed)
    deg = degrees(faces)
    for _ in range(k):
        es = undirected_edges(faces)
        u, v = es[rng.randrange(len(es))]
        if deg[u] <= 3 or deg[v] <= 3:
            continue
        nf = flip(faces, u, v)
        if nf is not None:
            faces = nf
            deg = degrees(faces)
    return faces


def random_triangulation(n, seed=None, mix=None):
    """Bipyramid base + random flips: tends to avoid degree-3 vertices."""
    rng = random.Random(seed)
    faces = bipyramid(n - 2)
    return random_flips(faces, mix if mix is not None else 10 * n,
                        seed=rng.randrange(1 << 30))


def contractible_neighbors(faces, v):
    """Neighbors u of v such that edge (v,u) is contractible keeping the
    triangulation simple: common neighbors of v,u are exactly the two
    opposite face vertices."""
    adj = adjacency(faces)
    third = edge_faces(faces)
    out = []
    for u in adj[v]:
        w, x = third[(v, u)], third[(u, v)]
        if adj[v] & adj[u] == {w, x}:
            out.append(u)
    return out


def contract(faces, v, u):
    """Contract edge (v,u), merging v into u.  Assumes contractibility."""
    out = []
    for f in faces:
        if v in f and u in f:
            continue
        out.append(tuple(u if t == v else t for t in f))
    return out
