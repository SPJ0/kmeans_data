"""Exhaustive enumeration of all simple sphere triangulations with n
vertices, by BFS in the flip graph (connected, by Wagner's theorem),
deduplicated by a canonical form of the combinatorial map (both
orientations, so reflections are identified).
"""

from collections import deque

from triangulations import (bipyramid, edge_faces, undirected_edges,
                            degrees, flip)


def canonical_form(faces):
    succ = edge_faces(faces)   # succ[(v,u)]: neighbor after u, ccw around v
    pred = {}
    for (v, u), w in succ.items():
        pred[(v, w)] = u
    best = None
    for table in (succ, pred):          # two orientations
        for root in table:
            a, b = root
            label = {a: 0, b: 1}
            order = [a, b]
            entry = {a: b, b: a}
            sig = []
            i = 0
            while i < len(order):
                v = order[i]
                i += 1
                start = entry[v]
                seq = []
                u = start
                while True:
                    if u not in label:
                        label[u] = len(order)
                        order.append(u)
                        entry[u] = v
                    seq.append(label[u])
                    u = table[(v, u)]
                    if u == start:
                        break
                sig.append(tuple(seq))
            t = tuple(sig)
            if best is None or t < best:
                best = t
    return best


def all_triangulations(n):
    """Yield one face-list per isomorphism class of n-vertex sphere
    triangulations."""
    start = bipyramid(n - 2)
    seen = {canonical_form(start)}
    queue = deque([start])
    yield start
    while queue:
        faces = queue.popleft()
        deg = degrees(faces)
        for u, v in undirected_edges(faces):
            if deg[u] <= 3 or deg[v] <= 3:
                continue
            nf = flip(faces, u, v)
            if nf is None:
                continue
            key = canonical_form(nf)
            if key not in seen:
                seen.add(key)
                queue.append(nf)
                yield nf
