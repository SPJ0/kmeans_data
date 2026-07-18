"""Tabulate the local data of the slope calculus.

For each ordered slope triple (p,q,r) (face boundary ccw), compute:
  * validity (rainbow: distinct; mono: equal; else invalid),
  * the face sign (slope-determined),
  * the base lambda pattern and the three corner bits
      r_i = mu_i XOR mu_{i+1}  (traversal coordinates).
Then search for closed forms: does the corner bit / sign have a nice
expression in terms of PG(1,3) structure (e.g. cross-ratio class,
permutation parity of the triple under a fixed ordering of slopes)?
"""
import sys
from itertools import permutations, product
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from affine_rep import det

SLOPES = [0, 1, 2, 'inf']
REP = {0: (1, 0), 1: (1, 1), 2: (1, 2), 'inf': (0, 1)}
SNUM = {0: 0, 1: 1, 2: 2, 'inf': 3}


def face_lambda_solutions(slopes3):
    w = [REP[s] for s in slopes3]
    sols = []
    for ls in product((1, 2), repeat=3):
        if all(sum(ls[i] * w[i][k] for i in range(3)) % 3 == 0
               for k in (0, 1)):
            sols.append(ls)
    return sols


def perm_parity(tri):
    """Parity of the permutation sorting tri (3 distinct comparables)."""
    a = [SNUM[t] for t in tri]
    inv = sum(1 for i in range(3) for j in range(i + 1, 3)
              if a[i] > a[j])
    return inv % 2


rows = []
for tri in permutations(SLOPES, 3):
    sols = face_lambda_solutions(tri)
    if not sols:
        rows.append((tri, None, None, None))
        continue
    base = tuple(0 if l == 1 else 1 for l in sols[0])
    corner = (base[0] ^ base[1], base[1] ^ base[2], base[2] ^ base[0])
    sign = (sols[0][0] * sols[0][1] * det(REP[tri[0]], REP[tri[1]])) % 3
    rows.append((tri, sign, corner, perm_parity(tri)))

print('%-14s %4s %10s %6s  %s' % ('triple', 'sign', 'corners',
                                  'parity', 'missing-slope'))
for tri, sign, corner, pp in rows:
    if sign is None:
        print('%-14s  INVALID' % (str(tri),))
        continue
    missing = [s for s in SLOPES if s not in tri][0]
    print('%-14s %4s %10s %6s  %s' % (tri, sign, corner, pp, missing))

# hypothesis tests
print()
ok_sign_parity = all(
    (sign == (1 if pp == 0 else 2)) or sign is None
    for tri, sign, corner, pp in rows)
print('sign == +1 iff even permutation of (0,1,2,inf) order:',
      ok_sign_parity)

# corner-bit hypotheses: try simple predicates
def test(name, fn):
    good = True
    for tri, sign, corner, pp in rows:
        if sign is None:
            continue
        pred = tuple(fn(tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3])
                     for i in range(3))
        if pred != corner:
            good = False
            break
    print('corner-bit rule %-40s: %s' % (name, good))

# corner between edges with slopes a (first) and b (second); c third slope
test('a<b in SNUM order', lambda a, b, c: 1 if SNUM[a] < SNUM[b] else 0)
test('a>b in SNUM order', lambda a, b, c: 1 if SNUM[a] > SNUM[b] else 0)
test('det(w_a,w_b) == 1', lambda a, b, c: 1 if det(REP[a], REP[b]) == 1
     else 0)
test('det(w_a,w_b) == 2', lambda a, b, c: 1 if det(REP[a], REP[b]) == 2
     else 0)
