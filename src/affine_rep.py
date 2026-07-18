"""Affine F_3^2 representations of sphere triangulations.

We seek phi : V -> F_3^2 and a face-sign pattern s(f) = det(phi(b)-phi(a),
phi(c)-phi(a)) mod 3 for ccw face (a,b,c) such that

  * every face has pairwise-distinct colors (automatic when s != 0,
    imposed explicitly when s == 0), and
  * no two faces sharing an edge have signs summing to 0 mod 3
    (forbidden adjacent sign pairs: (1,2), (2,1), (0,0)).

Theorem (proved in notes/): any such phi is a diagonal 9-coloring.
"""

from collections import defaultdict

from triangulations import edge_faces, undirected_edges, adjacency, vertex_set

F3SQ = [(x, y) for x in range(3) for y in range(3)]


def det(p, q):
    return (p[0] * q[1] - p[1] * q[0]) % 3


def face_sign(pa, pb, pc):
    return det(((pb[0] - pa[0]) % 3, (pb[1] - pa[1]) % 3),
               ((pc[0] - pa[0]) % 3, (pc[1] - pa[1]) % 3))


def _prepare(faces):
    verts = sorted(vertex_set(faces))
    adj = adjacency(faces)
    third = edge_faces(faces)
    # faces incident to each vertex
    vfaces = defaultdict(list)
    for i, f in enumerate(faces):
        for v in f:
            vfaces[v].append(i)
    # adjacent face pairs (sharing an edge)
    fpairs = defaultdict(list)   # face index -> list of adjacent face indices
    fidx = {}
    for i, (a, b, c) in enumerate(faces):
        for e in ((a, b), (b, c), (c, a)):
            fidx[e] = i
    for u, v in undirected_edges(faces):
        i, j = fidx[(u, v)], fidx[(v, u)]
        fpairs[i].append(j)
        fpairs[j].append(i)
    # diagonal pairs
    diag = defaultdict(set)
    for u, v in undirected_edges(faces):
        w, x = third[(u, v)], third[(v, u)]
        if w != x:
            diag[w].add(x)
            diag[x].add(w)
    return verts, adj, vfaces, fpairs, diag


def _vertex_order(faces, adj, start_face):
    order = list(start_face)
    placed = set(order)
    verts = vertex_set(faces)
    while len(order) < len(verts):
        best, bestk = None, -1
        for v in verts:
            if v in placed:
                continue
            k = sum(1 for u in adj[v] if u in placed)
            if k > bestk:
                best, bestk = v, k
        order.append(best)
        placed.add(best)
    return order


def solve_affine(faces, allow_zero=True, pure_sign=None, all_solutions=False):
    """Find phi (dict vertex -> F_3^2 point) satisfying the sign rules.

    pure_sign: if 1, force every face sign to be 1 (pure frieze case).
    Returns (phi, signs) or (None, None); if all_solutions, returns list.
    """
    verts, adj, vfaces, fpairs, diag = _prepare(faces)
    face_list = list(faces)
    nfaces = len(face_list)

    results = []
    # normalizations for the first face: sign 1, and (optionally) sign 0
    norms = [((0, 0), (1, 0), (0, 1))]
    if allow_zero and pure_sign is None:
        norms.append(((0, 0), (1, 0), (2, 0)))

    for norm in norms:
        f0 = face_list[0]
        phi = {f0[0]: norm[0], f0[1]: norm[1], f0[2]: norm[2]}
        signs = [None] * nfaces

        order = _vertex_order(faces, adj, f0)
        rest = order[3:]

        def face_ok(i):
            a, b, c = face_list[i]
            s = face_sign(phi[a], phi[b], phi[c])
            if s == 0:
                if pure_sign is not None or not allow_zero:
                    return None
                if len({phi[a], phi[b], phi[c]}) < 3:
                    return None
            if pure_sign is not None and s != pure_sign:
                return None
            for j in fpairs[i]:
                if signs[j] is not None and (s + signs[j]) % 3 == 0:
                    return None
            return s

        s0 = face_ok(0)
        if s0 is None:
            continue
        signs[0] = s0

        def bt(k):
            if k == len(rest):
                results.append((dict(phi), list(signs)))
                return not all_solutions
            v = rest[k]
            for p in F3SQ:
                if any(u in phi and phi[u] == p for u in adj[v]):
                    continue
                if any(u in phi and phi[u] == p for u in diag[v]):
                    continue
                phi[v] = p
                closed = []
                ok = True
                for i in vfaces[v]:
                    a, b, c = face_list[i]
                    if a in phi and b in phi and c in phi and signs[i] is None:
                        s = face_ok(i)
                        if s is None:
                            ok = False
                            break
                        signs[i] = s
                        closed.append(i)
                if ok and bt(k + 1):
                    return True
                for i in closed:
                    signs[i] = None
                del phi[v]
            return False

        if bt(0):
            if not all_solutions:
                phi, signs = results[-1]
                return phi, {tuple(face_list[i]): signs[i]
                             for i in range(nfaces)}
    if all_solutions and results:
        return results
    return (None, None) if not all_solutions else []


def verify_affine(faces, phi):
    """Check the sign rules directly and that phi diagonal-9-colors."""
    from diagonal import check_diagonal_coloring
    third = edge_faces(faces)
    fsign = {}
    for f in faces:
        a, b, c = f
        s = face_sign(phi[a], phi[b], phi[c])
        if len({phi[a], phi[b], phi[c]}) < 3:
            return False, "repeated color in face %s" % (f,)
        fsign[frozenset(f)] = (f, s)
    fidx = {}
    for f in faces:
        a, b, c = f
        for e in ((a, b), (b, c), (c, a)):
            fidx[e] = f
    for u, v in undirected_edges(faces):
        f1, f2 = fidx[(u, v)], fidx[(v, u)]
        s1 = fsign[frozenset(f1)][1]
        s2 = fsign[frozenset(f2)][1]
        if (s1 + s2) % 3 == 0:
            return False, "adjacent faces %s,%s have signs %d,%d" % (
                f1, f2, s1, s2)
    if not check_diagonal_coloring(faces, phi):
        return False, "not a diagonal coloring"
    return True, "ok"
