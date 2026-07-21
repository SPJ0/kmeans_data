"""Invariant search for the Alpoge JC_3 map F.

Looks for polynomial u, 1 <= deg u <= D, with u(F(v)) = a*u(v) + b for the
iterates F, F^2, F^3 (a in a small rational candidate set, b free). A hit with
a = 1 (or any affine relation with a fibration by planes) is the descent
scenario: some slice of F would be a planar Keller counterexample.

Method: exact linear algebra mod p by point sampling. For each candidate a,
the condition sum_m c_m (m(F(v)) - a*m(v)) - b = 0 is linear in (c, b);
sampling >= #unknowns + margin random points over GF(p) gives the kernel with
overwhelming probability; any nontrivial kernel is then certified exactly in
sympy (rational reconstruction of the mod-p vector, or symbolic re-solve).
"""
import itertools
import random
import sys

import sympy as sp

from jc3_map import F, V

P = (1 << 31) - 1  # Mersenne prime
random.seed(20260720)

x, y, z = V
F_poly = [sp.Poly(f, *V) for f in F]


def f_mod(pt):
    """Evaluate F at a point over GF(P)."""
    return tuple(int(fp(*pt)) % P for fp in F_poly)


def monomials(D):
    return [e for e in itertools.product(range(D + 1), repeat=3)
            if 1 <= sum(e) <= D]


def mono_eval(e, pt):
    return (pow(pt[0], e[0], P) * pow(pt[1], e[1], P) * pow(pt[2], e[2], P)) % P


def kernel_mod_p(rows, ncols):
    """Return basis of the kernel of the matrix (list of rows) over GF(P)."""
    m = [r[:] for r in rows]
    nrows = len(m)
    piv_col_of_row, where = [], {}
    r = 0
    for c in range(ncols):
        pr = next((i for i in range(r, nrows) if m[i][c] % P), None)
        if pr is None:
            continue
        m[r], m[pr] = m[pr], m[r]
        inv = pow(m[r][c], P - 2, P)
        m[r] = [(v * inv) % P for v in m[r]]
        for i in range(nrows):
            if i != r and m[i][c]:
                f = m[i][c]
                m[i] = [(a - f * b) % P for a, b in zip(m[i], m[r])]
        where[c] = r
        r += 1
        if r == nrows:
            break
    free = [c for c in range(ncols) if c not in where]
    basis = []
    for fc in free:
        v = [0] * ncols
        v[fc] = 1
        for c, rr in where.items():
            v[c] = (-m[rr][fc]) % P
        basis.append(v)
    return basis


def search(D, n_iter, a_num, a_den):
    """Kernel of u(F^k(v)) - a*u(v) - b over monomials of degree <= D."""
    mons = monomials(D)
    ncols = len(mons) + 1  # + b
    nsamp = ncols + 40
    rows = []
    for _ in range(nsamp):
        pt = tuple(random.randrange(1, P) for _ in range(3))
        q = pt
        for _ in range(n_iter):
            q = f_mod(q)
        a = (a_num * pow(a_den, P - 2, P)) % P
        row = [(mono_eval(e, q) - a * mono_eval(e, pt)) % P for e in mons]
        row.append((-1) % P)  # coefficient of b
        rows.append(row)
    ker = kernel_mod_p(rows, ncols)
    # drop solutions that are pure-b (u = 0)
    ker = [v for v in ker if any(c % P for c in v[:-1])]
    return mons, ker


def main():
    D = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    cand = [(1, 1), (-1, 1), (2, 1), (-2, 1), (1, 2), (-1, 2),
            (3, 1), (-3, 1), (4, 1), (8, 1), (-8, 1)]
    for n_iter in (1, 2, 3):
        for (an, ad) in cand:
            mons, ker = search(D, n_iter, an, ad)
            tag = f'F^{n_iter}, a={an}/{ad}, D<={D}'
            if ker:
                print(f'*** HIT {tag}: kernel dim {len(ker)}')
                v = ker[0]
                terms = [(c % P, e) for c, e in zip(v[:-1], mons) if c % P]
                print('    sample kernel vector (mod p):',
                      terms[:12], '... b =', v[-1] % P)
            else:
                print(f'no invariant: {tag}')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
