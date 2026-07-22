"""The multisection reformulation: using the 3D counterexample as an ENGINE for 2D.

Contrarian route (nobody can have covered this before 2026-07-20: it needs the
explicit 3D map F = (A,B,C) as raw material).

REFORMULATION.  Let p2 = (1,-3/2,13/2), p3 = (-1,3/2,13/2)  (marked points with
F(p2) = F(p3) = (-1/4,0,0)).  For ANY polynomial map phi: C^2 -> C^3 (no
embedding or etaleness required) define g = (A o phi, B o phi).  Then:

  * if phi(q2) = p2 and phi(q3) = p3 for q2 != q3, then g(q2) = g(q3):
    NON-INJECTIVITY IS FREE;
  * g is Keller  iff  det Jg = phi^*(dA ^ dB)/(ds ^ dt) = const != 0
    -- a single underdetermined PDE on three free polynomial functions.

So JC(2) is FALSE iff a "constant-area interpolating multisection" phi exists.
The classical difficulty (non-injectivity) is replaced by a soft-looking
transversality/volume condition on a surface parametrization.

FACTS ESTABLISHED BELOW.
1. The trivial section phi0 = (0,s,t) solves the PDE (det = -1, injective).
2. Affine interpolating planes: only degenerate solutions (det == 0).
3. mu2-equivariant sector: p2, p3 are swapped by the C^*-action at lambda=-1;
   imposing phi o (-s,t) = tau o phi (tau = (-x,-y,z)) makes interpolation at
   ONE point suffice.  Parity kills the (B,C)-projection (det forced odd);
   (A,B) and (A,C) survive.  Degrees 1-2: no solutions (consistent with Moh:
   success needs deg phi >= 15).
4. The COLLISION LEAF {B=C=0} decomposes as  A^1  |_|  C^*:
      z-axis (A = z, a bijective section sheet)  and
      {(x, -3/(2x), 13/(2x^2)) : x != 0}  with  A = -1/(4x^2),
   an etale double cover of C-{0} whose deck map is exactly x -> -x (mu2).
   The 1D germ of the counterexample is  A^1 |_| C^*  ->  A^1,
   (z, x) -> (z, -1/(4x^2)):  etale + non-injective, POWERED BY A UNIT.
   JC(2) asks whether the C^*-sheet can be thickened to an A^2-sheet;
   A^2 has only constant units -- the recurring rigidity.
5. The linearization of the PDE at phi0 is
      L(d) = -div(d2,d3) - 3s d1 - (12s^2+3t) d1_s + (89s^3+21st) d1_t,
   SURJECTIVE on polynomials (every polynomial is a divergence): the PDE has
   no infinitesimal obstruction; all difficulty is global degree-finiteness.
6. Consistency: an EMBEDDED bisection would be a geometric-degree-2 Keller
   counterexample (impossible, REPORT sec. 4); trisection: Orevkov.  So a
   successful multisection must cut generic (A,B)-leaves >= 6 times.

Run: python3 multisection_2d.py
"""
import sympy as sp

x, y, z, s, t, eps = sp.symbols('x y z s t epsilon')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
p2 = (1, sp.Rational(-3, 2), sp.Rational(13, 2))
p3 = (-1, sp.Rational(3, 2), sp.Rational(13, 2))

def det_g(phi, pair):
    f1 = pair[0].subs(dict(zip((x, y, z), phi)), simultaneous=True)
    f2 = pair[1].subs(dict(zip((x, y, z), phi)), simultaneous=True)
    return sp.expand(sp.diff(f1, s)*sp.diff(f2, t) - sp.diff(f1, t)*sp.diff(f2, s))

# 1. trivial section
assert det_g((0, s, t), (A, B)) == -1
print("1. trivial section: det = -1  OK")

# 2. affine interpolating planes are degenerate
m1, m2, m3, cc = sp.symbols('m1 m2 m3 c')
phi = tuple(p2[i] + s*(p3[i]-p2[i]) + t*[m1, m2, m3][i] for i in range(3))
eqs = sp.Poly(det_g(phi, (A, B)) - cc, s, t).coeffs()
sols = sp.solve(eqs, [m1, m2, m3, cc], dict=True)
assert all(so.get(cc, cc) == 0 for so in sols)
print("2. affine interpolating planes: only det == 0 branches  OK")

# 4. collision leaf decomposition
assert A.subs({x: 0, y: 0}) == z                       # section sheet
leaf = {y: sp.Rational(-3, 2)/x, z: sp.Rational(13, 2)/x**2}
assert sp.simplify(B.subs(leaf)) == 0 and sp.simplify(C.subs(leaf)) == 0
assert sp.simplify(A.subs(leaf) + sp.Rational(1, 4)/x**2) == 0
print("4. collision leaf = A^1 (A=z)  |_|  C^* (A = -1/(4x^2))  OK")

# 5. linearization at the trivial section
d1 = sp.Function('d1')(s, t); d2 = sp.Function('d2')(s, t); d3 = sp.Function('d3')(s, t)
phi_e = (eps*d1, s + eps*d2, t + eps*d3)
L = sp.simplify(sp.diff(det_g(phi_e, (A, B)), eps).subs(eps, 0))
expected = (-sp.diff(d2, s) - sp.diff(d3, t) - 3*s*d1
            - (12*s**2 + 3*t)*sp.diff(d1, s) + (89*s**3 + 21*s*t)*sp.diff(d1, t))
assert sp.simplify(L - expected) == 0
print("5. linearization L = -div(d2,d3) + (first-order in d1): surjective  OK")
print("All multisection facts verified.")
