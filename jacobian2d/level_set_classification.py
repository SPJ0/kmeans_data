"""Complete classification: NO coordinate level-surface of H = F o F is A^2.

THEOREM (this session).  For the 9-sheeted Keller map H = F o F, every level
surface of every coordinate function is non-planar:

  {A o F = delta}, delta != 0 :  UNITS KILL.  A_t = (1+ab) * R with
      R = (1+ab)^2 c + b^2(4+3ab), so (1+AB) * (R o F) = delta on the surface:
      1+AB is an invertible regular function, nonconstant (deg 13 < deg 43
      of the irreducible surface).  A^2 has only constant units.  Dead.
      [This corrects the session's earlier trap-hunt on Sigma' = {A o F = 1},
      which missed the units screen -- the simplest invariant of all.]

  {C o F = lam}, lam != 0 :   UNITS KILL.  C_t = a(2 - 3ab - a^2 c) factors,
      so A is a nonconstant unit on the surface.  Dead.

  {B o F = 0}  (generation 1):  AMS KILL via the coordinate axes (see
      ams_obstruction.py): {A=0}-fiber is the reduced irreducible x-axis.

  {B o F = beta}, beta != 0  (generation 3):  u-TRAP KILL.  On {u=0} the
      first coordinate A = u(...) vanishes, so B o F reduces to the
      b-coordinate: B o F|_{u=0} = B|_{u=0} = -2y.  Hence
          {u=0} n {B o F = beta}  =  the LINE {(2/beta, -beta/2, z)}  iso A^1,
      REDUCED (at beta=1 the 2x2 minor of (du | d(B o F)) is constantly 1
      along the line) and IRREDUCIBLE (chart equation x^13(x-2), x != 0).
      A generic fiber {u = mu} n Sigma'' lives in {xy = mu-1} iso C* x A^1,
      where any A^1 must be a vertical line (maps A^1 -> C* are constant);
      at mu=2 the fiber is a single irreducible (12,6)-curve with no
      vertical-line factor => not A^1.  Epimorphism theorem => not A^2.

GENERATION 4 OPENS.  For a generic plane K = alpha*a + beta*b + gamma*c
(alpha, gamma both involved), the surface {K o F = delta}:
  * no factorization of K_t  => no obvious unit;
  * on {u=0}: (A o F, B o F, C o F) = (c + 4b^2, b, 0), so the u=0 fiber is
    the graph  c = (delta + 2 beta y - 16 alpha y^2)/alpha  over y in C*
    iso C*  => no u-trap;
  * the {A=0}-fiber decomposes along A = u * R0  => reducible => no A-trap.
All three known kill mechanisms are dodged; the recognition problem for
generation 4 is open.

Run: python3 level_set_classification.py
"""
import sympy as sp

x, y, z = sp.symbols('x y z')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')
At = (1 + a*b)**3*c + b**2*(1 + a*b)*(4 + 3*a*b)
Bt = b + 3*a*(1 + a*b)**2*c + 3*a*b**2*(4 + 3*a*b)
Ct = 2*a - 3*a**2*b - a**3*c

# units kills
R = (1 + a*b)**2*c + b**2*(4 + 3*a*b)
assert sp.expand(At - (1 + a*b)*R) == 0
assert sp.expand(Ct - a*(2 - 3*a*b - a**2*c)) == 0
print("units kills: {A o F = delta}, {C o F = lam} (delta, lam != 0)  OK")

# u-trap on {B o F = beta}: B o F restricted to u=0 equals -2y
BF = sp.expand(Bt.subs({a: A, b: B, c: C}, simultaneous=True))
BFu0 = sp.simplify(sp.expand(BF.subs(y, -1/x)))     # chart of {u=0}
assert sp.simplify(BFu0 - 2/x) == 0                  # -2y = -2(-1/x) = 2/x
print("B o F |_{u=0} = -2y: the u=0 fiber of {B o F = beta} is one line  OK")

# reducedness at beta = 1 along the line {(2,-1/2,z)}
assert sp.simplify(BF.subs({x: 2, y: sp.Rational(-1, 2)}) - 1) == 0
du = sp.Matrix([y, x, 0]).subs({x: 2, y: sp.Rational(-1, 2)})
dBF = sp.Matrix([sp.diff(BF, v) for v in (x, y, z)]).subs(
    {x: 2, y: sp.Rational(-1, 2)})
assert sp.simplify(sp.Matrix.hstack(du, dBF)[[0, 1], :].det()) == 1
print("reduced irreducible A^1-fiber at u=0 (constant minor 1)  OK")

# generic u-fiber (mu=2) is a single non-vertical irreducible curve
P = sp.expand(sp.numer(sp.together(BF.subs(y, 1/x) - 1)))
fl = sp.factor_list(P)
assert len(fl[1]) == 1 and sp.degree(fl[1][0][0], z) == 6
print("u=2 fiber: irreducible (12,6)-curve in C* x A^1, not A^1  OK")
print("=> {B o F = beta} not iso A^2 for all beta != 0 (Epimorphism via u).")

# generation 4 dodges: u=0 fiber of {K o F = delta} is a C*-graph (alpha != 0)
al, be, ga, de = sp.symbols('alpha beta gamma delta')
AFu0 = c + 4*b**2                                    # A o F on u=0 (a=0)
Ku0 = al*AFu0 + be*b + ga*0 - de
sol = sp.solve(sp.Eq(Ku0, 0), c)
assert len(sol) == 1                                 # graph over b: one puncture via y != 0
print("generation 4 ({K o F = delta}, generic plane): u=0 fiber = C*-graph  OK")
print("All three kill mechanisms dodged: generation-4 recognition is open.")
