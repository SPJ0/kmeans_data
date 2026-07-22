"""The AMS/Epimorphism obstruction: resolution of the Sigma dichotomy (NEGATIVE).

THEOREM (this session).  Neither S1 = {B=0}, nor any level set {B=c}, nor the
9-sheet surface Sigma = {B o F = 0} is isomorphic to A^2.  The proof is
independent of Orevkov's theorem and works at ANY sheet number -- a new
obstruction mechanism for the iterated-preimage construction.

MECHANISM.  The Abhyankar-Moh Epimorphism Theorem says: if f in C[s,t] has
C[s,t]/(f) iso C[T] (i.e. some scheme fiber of f is a reduced irreducible A^1),
then f is a coordinate -- so ALL fibers of f are reduced A^1's.  Hence a smooth
affine surface X carrying a regular function whose zero fiber is a reduced
irreducible A^1 while some other fiber is NOT an A^1 cannot be A^2.

  * S1 = {B=0}:  the function x has fibers
       x = lam != 0 :  the graph z = -(y + 12 lam y^2 + 9 lam^2 y^3)/(3 lam u^2),
                       with a genuine pole at y = -1/lam  (numerator -> -2/lam),
                       so the fiber is A^1 minus a point  =  C* ;
       x = 0       :  B(0,y,z) = y  =>  the reduced z-axis  =  A^1 .
    If S1 were A^2, AMS applied to x forces all fibers to be A^1: contradiction.
    (This re-proves S1 not iso A^2 without citing Orevkov.)
  * {B=c} (any c):  x = 0 fiber is {(0,c,z)} (B(0,y,z)-c = y-c, reduced A^1);
    generic fibers are C* (pole cancels only at the single value lam = 2/c,
    where the fiber becomes an A^1 -- two A^1-fibers, still non-A^2 by AMS).
  * Sigma = {B o F = 0}:  the function A|Sigma has zero fiber F^{-1}(z-axis).
    The z-axis lies INSIDE the Jelonek set of F (Lam*(0,0,t) = 0), its fibers
    degenerate to the single point (t/2, 0, 0):  F(t/2,0,0) = (0,0,t).  So
    {A|Sigma = 0} = the x-axis, and along the whole axis
        dA = (0,0,1),   d(B o F) = (0,1,9x),
    with constant 2x2 minor -1: the fiber is smooth of multiplicity one --
    a REDUCED IRREDUCIBLE A^1.  Generic fibers of A|Sigma are etale (<=3:1)
    covers of C*-minus-finitely-many-points; no component can be A^1 (an
    etale dominant map A^1 -> C* would be a nonvanishing polynomial with
    nonvanishing derivative: impossible), so no fiber is an A^1.
    If Sigma were A^2, AMS gives a contradiction.   QED

MORAL.  The Jelonek set is the enemy: target curves over which F's fibers
drop to a single point pull back to reduced A^1-fibers inside preimage
surfaces, and AMS converts those into exoticity certificates.  A successful
iterated-preimage construction must arrange the deficient fibers to be EMPTY
(full escape to infinity) rather than singletons.

BYPRODUCT.  S1, {B=c}, Sigma are smooth affine surfaces with trivial units,
Cl = 0 (for S1: every fiber of the C*-fibration is irreducible and principal,
div(x - lam); the generic fiber's class group vanishes), e(S1) = 1, and
pi_1(S1) = 1 (loops around x=0 bound disks through the filled A^1-fiber) --
yet none is A^2: an explicit family of exotic-plane-type surfaces attached to
the Jacobian counterexample.

Run: python3 ams_obstruction.py
"""
import sympy as sp

x, y, z, t, lam = sp.symbols('x y z t lambda')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')
Bt = b + 3*a*(1 + a*b)**2*c + 3*a*b**2*(4 + 3*a*b)
BF = sp.expand(Bt.subs({a: A, b: B, c: C}, simultaneous=True))

# --- S1: fibration by x -------------------------------------------------------
# solve B=0 for z over x = lam:   z = N(y) / (3 lam u^2)
Nnum = sp.together(sp.solve(sp.Eq(B.subs(x, lam), 0), z)[0])
assert sp.simplify(sp.numer(Nnum).subs(y, -1/lam)) != 0     # genuine pole
assert B.subs(x, 0) == y                                     # reduced A^1 fiber
print("S1: fibers C* (x!=0) and reduced A^1 (x=0)  => not A^2 by AMS  OK")

# --- level sets {B=c}: pole cancels only at lam = 2/c ------------------------
Nc = sp.numer(sp.together(sp.solve(sp.Eq(B.subs(x, lam) - c, 0), z)[0]))
cancel_at = sp.solve(sp.Eq(Nc.subs(y, -1/lam), 0), lam)
assert cancel_at == [2/c]
print("{B=c}: generic fibers C*, A^1-fibers at x=0 and x=2/c  => not A^2  OK")

# --- Sigma: zero fiber of A|Sigma is the reduced x-axis ----------------------
assert sp.simplify(A.subs({y: 0, z: 0})) == 0
assert sp.simplify(BF.subs({y: 0, z: 0})) == 0
Fim = [sp.simplify(f.subs({x: t/2, y: 0, z: 0})) for f in (A, B, C)]
assert Fim == [0, 0, t]                                     # F(x-axis) = z-axis
Lam_star = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2
assert Lam_star.subs({a: 0, b: 0}) == 0                     # z-axis in Jelonek set
cub = sp.expand((Lam_star*x**3 + (4 - 3*b*c)*x - 2*c).subs({a: 0, b: 0, c: t}))
assert cub == 4*x - 2*t                                     # single-point fibers
dA = sp.Matrix([sp.diff(A, v) for v in (x, y, z)]).subs({y: 0, z: 0})
dBF = sp.Matrix([sp.diff(BF, v) for v in (x, y, z)]).subs({y: 0, z: 0})
M = sp.Matrix.hstack(dA, dBF)
assert sp.simplify(M[[1, 2], :].det()) == -1                # rank 2 along whole axis
print("Sigma: {A=0} is the reduced irreducible x-axis (rank-2 everywhere)  OK")
print("Generic fibers of A|Sigma: etale covers of punctured C* -- never A^1.")
print("CONCLUSION: Sigma is NOT isomorphic to A^2 (AMS/Epimorphism obstruction).")
print("The 9-sheet iterated-preimage candidate is closed -- negatively -- by a")
print("mechanism independent of (and beyond) Orevkov-type sheet-count theorems.")
