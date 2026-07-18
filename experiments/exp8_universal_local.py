"""Universal local extension check at a degree-d site.

Data: ring colors c_1..c_d in F_3^2 (cyclic; constraints: consecutive
and second-neighbor pairs distinct — for d <= 5 this makes the tuple
rainbow), and outer face signs sigma_1..sigma_d in F_3.

Question: does there exist p in F_3^2 such that with
s_i = det(c_i - p, c_{i+1} - p):
  (i)   p != c_i for all i           (face injectivity),
  (ii)  s_i + s_{i+1} != 0 (mod 3)   (adjacent star faces),
  (iii) s_i + sigma_i != 0 (mod 3)   (star face vs outer face)?

By Theorem 1, a yes gives a valid affine extension no matter what the
ambient triangulation looks like.  We test ALL (c, sigma): a 'UNIVERSAL'
verdict is a finite-check theorem.
"""
import sys, time
from itertools import product, permutations
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

F3SQ = [(x, y) for x in range(3) for y in range(3)]
IDX = {p: i for i, p in enumerate(F3SQ)}


def det(p, q):
    return (p[0] * q[1] - p[1] * q[0]) % 3


def sgn(p, a, b):
    return det(((a[0]-p[0]) % 3, (a[1]-p[1]) % 3),
               ((b[0]-p[0]) % 3, (b[1]-p[1]) % 3))


def ring_tuples(d):
    """Cyclic tuples with consecutive and second-neighbor distinctness,
    with c_1 = (0,0) fixed (translation normalization)."""
    out = []
    def ok(tup, nxt):
        k = len(tup)
        if k >= 1 and nxt == tup[-1]:
            return False
        if k >= 2 and nxt == tup[-2]:
            return False
        if k == d - 1:
            if nxt == tup[0] or (d > 2 and nxt == tup[1]):
                return False
            if d > 2 and tup[0] == tup[-1]:
                return False
        return True
    def rec(tup):
        if len(tup) == d:
            # full cyclic second-neighbor check
            for i in range(d):
                if tup[i] == tup[(i+1) % d] or tup[i] == tup[(i+2) % d]:
                    return
            out.append(tuple(tup))
            return
        for p in F3SQ:
            if ok(tup, p):
                rec(tup + [p])
    rec([(0, 0)])
    return out


def universal_check(d, verbose=True):
    t0 = time.time()
    rings = ring_tuples(d)
    total_bad = 0
    examples = []
    full = (1 << 9) - 1
    sigmas = list(product(range(3), repeat=d))
    for c in rings:
        # candidate centers p: not equal to any ring color
        cand = [p for p in F3SQ if p not in c]
        # mutual conditions + per-position kill masks
        kill = [[0] * 3 for _ in range(d)]   # kill[i][t]: p killed if sigma_i = t
        okmask = 0
        svecs = {}
        for p in cand:
            s = [sgn(p, c[i], c[(i + 1) % d]) for i in range(d)]
            if any((s[i] + s[(i + 1) % d]) % 3 == 0 for i in range(d)):
                continue
            okmask |= 1 << IDX[p]
            svecs[p] = s
            for i in range(d):
                kill[i][(-s[i]) % 3] |= 1 << IDX[p]
        if okmask == 0:
            total_bad += len(sigmas)
            if len(examples) < 3:
                examples.append((c, None, 'no p passes mutual conditions'))
            continue
        for sig in sigmas:
            killed = 0
            for i in range(d):
                killed |= kill[i][sig[i]]
            if okmask & ~killed == 0:
                total_bad += 1
                if len(examples) < 6:
                    examples.append((c, sig, 'blocked'))
    verdict = 'UNIVERSAL' if total_bad == 0 else 'FAILS'
    print('d=%d: rings=%d sigma-combos=%d  -> %s (bad cases: %d) [%.0fs]' %
          (d, len(rings), len(sigmas), verdict, total_bad, time.time() - t0))
    for e in examples:
        print('   e.g.', e)
    return total_bad == 0


if __name__ == '__main__':
    for d in (3, 4, 5):
        universal_check(d)
