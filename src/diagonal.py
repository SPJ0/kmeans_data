"""Diagonal conflict graph and exact coloring for sphere triangulations.

Diagonal coloring: vertices of a common face get distinct colors, and for
every edge {u,v} the two opposite vertices w, x of the two faces on {u,v}
get distinct colors.
"""

from collections import defaultdict

from triangulations import edge_faces, undirected_edges, vertex_set


def diagonal_graph(faces):
    """Conflict graph as dict vertex -> set of conflicting vertices."""
    conf = defaultdict(set)
    third = edge_faces(faces)
    for u, v in undirected_edges(faces):
        conf[u].add(v)
        conf[v].add(u)
        w, x = third[(u, v)], third[(v, u)]
        if w != x:
            conf[w].add(x)
            conf[x].add(w)
    return conf


def color_graph(conf, k, order=None):
    """Backtracking k-coloring with DSATUR-style dynamic ordering.

    Returns dict vertex -> color in range(k), or None.
    """
    verts = list(conf.keys())
    color = {}
    neigh_colors = {v: set() for v in verts}

    def pick():
        best, best_key = None, None
        for v in verts:
            if v in color:
                continue
            key = (len(neigh_colors[v]), len(conf[v]))
            if best is None or key > best_key:
                best, best_key = v, key
        return best

    def bt():
        v = pick()
        if v is None:
            return True
        used = neigh_colors[v]
        if len(used) >= k:
            return False
        for c in range(k):
            if c in used:
                continue
            color[v] = c
            touched = []
            for u in conf[v]:
                if u not in color and c not in neigh_colors[u]:
                    neigh_colors[u].add(c)
                    touched.append(u)
            if bt():
                return True
            del color[v]
            for u in touched:
                neigh_colors[u].discard(c)
        return False

    return dict(color) if bt() else None


def greedy_clique_lb(conf):
    verts = sorted(conf, key=lambda v: -len(conf[v]))
    clique = []
    for v in verts:
        if all(v in conf[u] for u in clique):
            clique.append(v)
    return len(clique)


def diagonal_chromatic_number(faces, kmax=12):
    conf = diagonal_graph(faces)
    lb = greedy_clique_lb(conf)
    for k in range(lb, kmax + 1):
        col = color_graph(conf, k)
        if col is not None:
            return k, col
    return None, None


def check_diagonal_coloring(faces, color):
    third = edge_faces(faces)
    for u, v in undirected_edges(faces):
        if color[u] == color[v]:
            return False
        w, x = third[(u, v)], third[(v, u)]
        if w != x and color[w] == color[x]:
            return False
    return True
