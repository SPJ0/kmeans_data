"""Completion of Theorem 6: capped antiprisms via closed-walk lengths.

Boolean matrix powers of the transfer digraph H (from
exp14_antiprism_theorem) find a node with closed walks of coprime
lengths 3 and 5 (Frobenius number 7): all m >= 8 follow by composition
at that node; m = 3..7 are verified by direct solving.  Composed
representations independently verified for m = 8..36, 100, 101, 500,
503.  Result: every capped antiprism (ring vertices of degree 5;
m = 5 is the icosahedron) admits an affine representation.
"""
import sys
from math import gcd
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/experiments')

from exp14_antiprism_theorem import (build_H, capped_antiprism,
                                     rep_from_walk, cycles_through)
from triangulations import check_triangulation
from affine_rep import solve_affine, verify_affine

if __name__ == '__main__':
    nodes, succ = build_H()
    N = len(nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    rows = [0] * N
    for n, ss in succ.items():
        for s2 in ss:
            rows[idx[n]] |= 1 << idx[s2]
    cur = list(rows)
    loops = {}
    for k in range(2, 16):
        nxt = [0] * N
        for i in range(N):
            r, m_ = 0, cur[i]
            while m_:
                b = m_ & -m_
                r |= rows[b.bit_length() - 1]
                m_ ^= b
            nxt[i] = r
        cur = nxt
        for i in range(N):
            if cur[i] >> i & 1:
                loops.setdefault(i, set()).add(k)
    best = None
    for i, ls in loops.items():
        for a in sorted(ls):
            for b in sorted(ls):
                if gcd(a, b) == 1:
                    f = a * b - a - b
                    if best is None or f < best[0]:
                        best = (f, i, a, b)
    frob, i0, a, b = best
    la = cycles_through(succ, nodes[i0], a)
    lb = cycles_through(succ, nodes[i0], b)
    print('base', nodes[i0], 'loop lengths', a, b, 'Frobenius', frob)

    def compose(m):
        for cb in range(m // b + 1):
            rest = m - b * cb
            if rest >= 0 and rest % a == 0:
                return la[:-1] * (rest // a) + lb[:-1] * cb
        return None

    ok_all = True
    for m in list(range(frob + 1, frob + 30)) + [100, 101, 500, 503]:
        faces = capped_antiprism(m)
        check_triangulation(faces)
        ok, msg = verify_affine(faces, rep_from_walk(compose(m), m))
        ok_all &= ok
    print('large m verified:', ok_all)
    small = all(
        (lambda p: p[0] is not None and
         verify_affine(capped_antiprism(m), p[0])[0])(
            solve_affine(capped_antiprism(m)))
        for m in range(3, frob + 1))
    print('small m=3..%d verified: %s' % (frob, small))
