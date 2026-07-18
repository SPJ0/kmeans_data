"""Verify the slope-field decomposition claims on solved instances.

For an affine representation phi with edge tension z(e) = phi(v)-phi(u):
  * slope(e) = class of z(e) in PG(1,3)  (4 slopes)
  * Claim R: every face is rainbow (3 distinct slopes, sign != 0) or
    mono (all three z equal, sign 0).
  * Claim S: for a rainbow face, the sign is determined by the slope
    triple together with its cyclic order (independent of the +-1
    magnitudes), i.e. equal faces-slope-data => equal sign.  We verify
    by recomputing the sign from slopes via canonical representatives
    and comparing, over many representations and instances.
"""
import sys, time
from collections import defaultdict
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from triangulations import (random_triangulation, icosahedron,
                            vertex_set)
from affine_rep import solve_affine, verify_affine, face_sign, det

# slope of a nonzero vector in F_3^2: an element of {0,1,2,'inf'}
def slope(z):
    x, y = z
    if x % 3 == 0:
        return 'inf'
    return (y * pow(x, 1, 3)) % 3 if x % 3 == 1 else (y * 2) % 3


REP = {0: (1, 0), 1: (1, 1), 2: (1, 2), 'inf': (0, 1)}


def diff(p, q):
    return ((q[0] - p[0]) % 3, (q[1] - p[1]) % 3)


def check_instance(faces, phi):
    ok_R = ok_S = True
    for (a, b, c) in faces:
        pa, pb, pc = phi[a], phi[b], phi[c]
        z1, z2, z3 = diff(pa, pb), diff(pb, pc), diff(pc, pa)
        s = face_sign(pa, pb, pc)
        slopes = (slope(z1), slope(z2), slope(z3))
        if s == 0:
            if not (z1 == z2 == z3):
                ok_R = False
        else:
            if len(set(slopes)) != 3:
                ok_R = False
            # sign from canonical representatives of the slopes, using
            # the same cyclic order (z1, z2):
            w1, w2 = REP[slopes[0]], REP[slopes[1]]
            s_pred_up_to_sign = det(w1, w2)
            # claim: lambda1*lambda2 is forced by the closedness pattern:
            # z_i = l_i * w_i with l_i = +-1 and sum zero; solve for l's
            sols = []
            for l1 in (1, 2):
                for l2 in (1, 2):
                    for l3 in (1, 2):
                        z1p = ((l1 * w1[0]) % 3, (l1 * w1[1]) % 3)
                        z2p = ((l2 * w2[0]) % 3, (l2 * w2[1]) % 3)
                        w3 = REP[slopes[2]]
                        z3p = ((l3 * w3[0]) % 3, (l3 * w3[1]) % 3)
                        if ((z1p[0] + z2p[0] + z3p[0]) % 3 == 0 and
                                (z1p[1] + z2p[1] + z3p[1]) % 3 == 0):
                            sols.append((l1, l2, l3))
            prods = {(l1 * l2) % 3 for l1, l2, l3 in sols}
            if len(prods) != 1:
                ok_S = False
            else:
                s_pred = (list(prods)[0] * s_pred_up_to_sign) % 3
                if s_pred != s:
                    ok_S = False
    return ok_R, ok_S


if __name__ == '__main__':
    allR = allS = True
    tested = 0
    cases = [icosahedron()] + [random_triangulation(n, seed=s)
                               for n in (10, 14, 18, 24) for s in range(4)]
    for faces in cases:
        sols = solve_affine(faces, all_solutions=True, max_solutions=60)
        for phi, _ in sols:
            r, s = check_instance(faces, phi)
            allR &= r
            allS &= s
            tested += 1
    print('representations tested: %d' % tested)
    print('Claim R (rainbow-or-mono faces): %s' % allR)
    print('Claim S (sign determined by slope data + cyclic order): %s' % allS)
