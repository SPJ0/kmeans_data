import sys, time
sys.path.insert(0, __file__.rsplit('/', 2)[0] + '/src')

from enumerate_all import all_triangulations
from diagonal import diagonal_chromatic_number
from affine_rep import solve_affine, verify_affine

# known counts of simple sphere triangulations by n
KNOWN = {4: 1, 5: 1, 6: 2, 7: 5, 8: 14, 9: 50, 10: 233, 11: 1249}

if __name__ == '____main__' or True:
    nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    do_chi = '--chi' in sys.argv
    for n in range(5, nmax + 1):
        t0 = time.time()
        count = 0
        fails = []
        chimax = 0
        for faces in all_triangulations(n):
            count += 1
            phi, signs = solve_affine(faces)
            if phi is None:
                fails.append(list(faces))
            else:
                ok, msg = verify_affine(faces, phi)
                assert ok, (msg, faces)
            if do_chi:
                chi, _ = diagonal_chromatic_number(faces)
                chimax = max(chimax, chi)
        expect = KNOWN.get(n, '?')
        print('n=%2d: %d triangulations (expected %s), affine failures: %d,'
              ' max chi_diag: %s  (%.1fs)' %
              (n, count, expect, len(fails),
               chimax if do_chi else '-', time.time() - t0))
        for f in fails[:5]:
            print('   FAIL:', f)
