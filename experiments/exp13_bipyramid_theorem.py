"""Theorem 5 (machine-assisted): every bipyramid admits an affine
representation, hence a diagonal 9-coloring.

Method: fix apex colors A=(0,0), B=(1,1).  All constraints of
bipyramid(m) are windowed over consecutive ring triples, so valid ring
colorings = closed walks of length m in the digraph H:
  nodes: ordered pairs (p,q) of distinct colors from F_3^2 - {A,B}
         such that faces T=(A,p,q) and B'=(B,q,p) are valid shapes and
         sign-compatible with each other;
  edges: (p,q) -> (q,r) iff T(p,q) ~ T(q,r) compatible and
         B'(p,q) ~ B'(q,r) compatible.
We exhibit closed walks of lengths 4 and 5 through a common node;
composition gives every length m >= 12 (Frobenius number of {4,5} is
11), and m in 3..11 is verified by direct solving.  Every constructed
representation is verified independently with verify_affine.
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import bipyramid
from affine_rep import face_sign, solve_affine, verify_affine

A, B = (0, 0), (1, 1)
COLORS = [(x, y) for x in range(3) for y in range(3)
          if (x, y) not in (A, B)]


def shape_ok(f):
    """Face triple valid: distinct colors (sign 0 allowed => AP, which
    is automatic given distinctness and det 0)."""
    return len(set(f)) == 3


def compat(s1, s2):
    return (s1 + s2) % 3 != 0


def node_ok(p, q):
    if p == q:
        return False
    t = (A, p, q)
    bo = (B, q, p)
    if not (shape_ok(t) and shape_ok(bo)):
        return False
    st = face_sign(*t)
    sb = face_sign(*bo)
    return compat(st, sb)


def edge_ok(p, q, r):
    st1, st2 = face_sign(A, p, q), face_sign(A, q, r)
    sb1, sb2 = face_sign(B, q, p), face_sign(B, r, q)
    return compat(st1, st2) and compat(sb1, sb2)


def build_H():
    nodes = [(p, q) for p in COLORS for q in COLORS if node_ok(p, q)]
    succ = {n: [] for n in nodes}
    for (p, q) in nodes:
        for r in COLORS:
            if (q, r) in succ and edge_ok(p, q, r):
                succ[(p, q)].append((q, r))
    return nodes, succ


def cycles_through(succ, start, length):
    """A closed walk of given length from start back to start."""
    def dfs(node, k, path):
        if k == length:
            return path if node == start else None
        for nxt in succ[node]:
            res = dfs(nxt, k + 1, path + [nxt])
            if res:
                return res
        return None
    return dfs(start, 0, [start])


def ring_from_walk(walk):
    return [n[0] for n in walk]


def rep_for_m(m, base, loop4, loop5):
    """Compose loops at the base node to length m, return ring colors."""
    # m = 4*a + 5*b
    for b_cnt in range(0, m // 5 + 1):
        rest = m - 5 * b_cnt
        if rest >= 0 and rest % 4 == 0:
            a_cnt = rest // 4
            walk = []
            for _ in range(a_cnt):
                walk += loop4[:-1] if walk else loop4[:-1]
            for _ in range(b_cnt):
                walk += loop5[:-1]
            return ring_from_walk(walk + [base])[:-1]
    return None


if __name__ == '__main__':
    nodes, succ = build_H()
    print('H: %d nodes, %d edges' % (len(nodes),
                                     sum(len(v) for v in succ.values())))
    base = None
    l4 = l5 = None
    for n in nodes:
        c4 = cycles_through(succ, n, 4)
        c5 = cycles_through(succ, n, 5)
        if c4 and c5:
            base, l4, l5 = n, c4, c5
            break
    print('base node:', base)
    print('loop4 ring:', ring_from_walk(l4[:-1]))
    print('loop5 ring:', ring_from_walk(l5[:-1]))

    # verify composition for a wide range of m (spot: 12..60 and jumps)
    all_ok = True
    for m in list(range(12, 61)) + [100, 101, 102, 103, 1000, 1001]:
        ring = rep_for_m(m, base, l4, l5)
        assert ring is not None and len(ring) == m, m
        faces = bipyramid(m)
        phi = {m: A, m + 1: B}
        for i, c in enumerate(ring):
            phi[i] = c
        ok, msg = verify_affine(faces, phi)
        if not ok:
            print('m=%d FAILED: %s' % (m, msg))
            all_ok = False
    print('composed representations verified for m=12..60, 100..103,'
          ' 1000, 1001:', all_ok)

    # small cases 3..11 by direct solving
    small_ok = True
    for m in range(3, 12):
        phi, _ = solve_affine(bipyramid(m))
        ok = phi is not None and verify_affine(bipyramid(m), phi)[0]
        small_ok &= ok
    print('small cases m=3..11 solvable:', small_ok)
