"""Theorem 6 (machine-assisted): every capped antiprism (gyroelongated
bipyramid; m=5 is the icosahedron) admits an affine representation.
Ring vertices all have degree 5, so this is an infinite family inside
the minimum-degree-5 class (apex degrees are m).

Transfer digraph: nodes are color 4-tuples (u_i, w_i, u_{i+1}, w_{i+1})
(apex colors fixed); edges advance the window by one rung and check all
constraints involving three consecutive rungs.  Loops of coprime
lengths at a common node + direct small cases cover every m >= 3.
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import check_triangulation
from affine_rep import face_sign, solve_affine, verify_affine

A, B = (0, 0), (1, 1)
COLORS = [(x, y) for x in range(3) for y in range(3)
          if (x, y) not in (A, B)]


def capped_antiprism(m):
    u = list(range(m))
    w = list(range(m, 2 * m))
    a, b = 2 * m, 2 * m + 1
    faces = []
    for i in range(m):
        j = (i + 1) % m
        faces.append((a, u[i], u[j]))
        faces.append((u[i], w[i], u[j]))
        faces.append((u[j], w[i], w[j]))
        faces.append((b, w[j], w[i]))
    return faces


def compat(s1, s2):
    return (s1 + s2) % 3 != 0


def distinct(*cs):
    return len(set(cs)) == len(cs)


def rung_faces(ui, wi, uj, wj):
    """Faces fully inside window (i, i+1): belt pair + none of caps."""
    return [(ui, wi, uj), (uj, wi, wj)]


def window_ok(ui, wi, uj, wj):
    for f in rung_faces(ui, wi, uj, wj) + [(A, ui, uj), (B, wj, wi)]:
        if not distinct(*f):
            return False
    b1 = face_sign(ui, wi, uj)
    b2 = face_sign(uj, wi, wj)
    t = face_sign(A, ui, uj)
    cb = face_sign(B, wj, wi)
    # compat: T_i~belt1_i, belt1~belt2, belt2~capB_i
    return (compat(t, b1) and compat(b1, b2) and compat(b2, cb))


def edge_ok(n1, n2):
    ui, wi, uj, wj = n1
    uj2, wj2, uk, wk = n2
    if (uj, wj) != (uj2, wj2):
        return False
    # constraints spanning two windows: T_i~T_{i+1}, capB_i~capB_{i+1},
    # belt2_i~belt1_{i+1}
    t1, t2 = face_sign(A, ui, uj), face_sign(A, uj, uk)
    c1, c2 = face_sign(B, wj, wi), face_sign(B, wk, wj)
    b2i = face_sign(uj, wi, wj)
    b1k = face_sign(uj, wj, uk)
    return compat(t1, t2) and compat(c1, c2) and compat(b2i, b1k)


def build_H():
    nodes = [(u1, w1, u2, w2)
             for u1 in COLORS for w1 in COLORS
             for u2 in COLORS for w2 in COLORS
             if window_ok(u1, w1, u2, w2)]
    nodeset = set(nodes)
    succ = {n: [] for n in nodes}
    for n in nodes:
        uj, wj = n[2], n[3]
        for uk in COLORS:
            for wk in COLORS:
                n2 = (uj, wj, uk, wk)
                if n2 in nodeset and edge_ok(n, n2):
                    succ[n].append(n2)
    return nodes, succ


def cycles_through(succ, start, length, limit=2_000_000):
    cnt = [0]
    def dfs(node, k, path):
        cnt[0] += 1
        if cnt[0] > limit:
            return None
        if k == length:
            return path if node == start else None
        for nxt in succ[node]:
            res = dfs(nxt, k + 1, path + [nxt])
            if res:
                return res
        return None
    return dfs(start, 0, [start])


def rep_from_walk(walk, m):
    phi = {2 * m: A, 2 * m + 1: B}
    for i in range(m):
        ui, wi, _, _ = walk[i]
        phi[i] = ui
        phi[m + i] = wi
    return phi


if __name__ == '__main__':
    nodes, succ = build_H()
    print('H: %d nodes, %d edges' % (len(nodes),
                                     sum(len(v) for v in succ.values())))
    base = l4 = l5 = None
    for n in nodes:
        c4 = cycles_through(succ, n, 4)
        if not c4:
            continue
        c5 = cycles_through(succ, n, 5)
        if c5:
            base, l4, l5 = n, c4, c5
            break
    print('base node:', base)
    assert base is not None

    def compose(m):
        for b_cnt in range(m // 5 + 1):
            rest = m - 5 * b_cnt
            if rest >= 0 and rest % 4 == 0:
                walk = []
                for _ in range(rest // 4):
                    walk += l4[:-1]
                for _ in range(b_cnt):
                    walk += l5[:-1]
                return walk
        return None

    all_ok = True
    for m in list(range(12, 41)) + [100, 101, 500, 503]:
        walk = compose(m)
        faces = capped_antiprism(m)
        check_triangulation(faces)
        phi = rep_from_walk(walk, m)
        ok, msg = verify_affine(faces, phi)
        if not ok:
            all_ok = False
            print('m=%d FAILED %s' % (m, msg))
    print('composed reps verified (m=12..40,100,101,500,503):', all_ok)

    small_ok = True
    for m in range(3, 12):
        faces = capped_antiprism(m)
        check_triangulation(faces)
        phi, _ = solve_affine(faces)
        ok = phi is not None and verify_affine(faces, phi)[0]
        if not ok:
            print('small m=%d FAILED' % m)
        small_ok &= ok
    print('small cases m=3..11 solvable (m=5 is the icosahedron):',
          small_ok)
