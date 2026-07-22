"""Sigma' = {A o F = 1}: the second-generation A^2-candidate, dodging the AMS trap.

LESSON FROM THE FIRST CANDIDATE.  Sigma = {B o F = 0} died by the AMS/Epimorphism
obstruction because the z-axis (the x=0 fiber of the C*-fibration on S1 = {B=0})
lies inside the Jelonek set of F with SINGLETON fibers, so A|Sigma acquired a
reduced irreducible A^1 zero-fiber.  Checked: this is FAMILY-WIDE for {b=const}
planes -- the (8,7,5) instance has the same collapse (fiber cubic -> 2(2x-t)
over the z-axis), forced by a0, b0 being divisible by w^2, w.

THE ESCAPE.  Classify first-level planes P and the induced trap:
  * P = {b = const}:   x=0 fiber of S_P is the z-axis, INSIDE the Jelonek set
    (Lam*(0,0,t) = 0): singleton fibers  =>  irreducible A^1  =>  AMS kills.
  * P = {c = const}:   S_P iso C* x A^1 (units obstruction; the defect surface).
  * P = {a = delta}, delta != 0:  the x=0 fiber of S_P is the parabola
    L_P = {(0, y, delta - 4y^2)} iso A^1, but L_P meets the Jelonek set
    {Lam* = 0} = {a=0: b^2(bc-1) = 0} only in FINITELY many points -- fibers
    over L_P are generically 3 points, NOT singletons.  Moreover
        A = u * (u^2 z + y^2(4+3xy)),        u = 1+xy,
    so the zero fiber F^{-1}(L_P) of the would-be trap function A|Sigma' is
    REDUCIBLE:  a C*-component  {x = -1/y, z = -16y^5+y^3+5y^2}  (delta=1)
    on {u=0}, plus a separate plane-curve component of bidegree (2,4).
    The Epimorphism theorem requires an IRREDUCIBLE reduced A^1-fiber:
    the known obstruction fails structurally.

THE CANDIDATE.
    Sigma' = {A o F = 1}:  irreducible hypersurface of degree 43, smooth
    (etale preimage of the smooth plane {a=1}), carrying the 9:1 etale map
    (B o F, C o F)|Sigma'  ->  {a=1} iso A^2, with 9-point generic fibers
    (collisions built in everywhere).

    Sigma' iso A^2   <=>  JC(2) is false.
    No known obstruction applies:  9 sheets is beyond Orevkov-type theorems,
    and the AMS trap is dodged as above.

NEXT (the trap-hunt protocol, before any positive tools): enumerate natural
functions on Sigma' (B o F, C o F, x, y, z, u, low-degree combinations) and
check whether any has a reduced irreducible A^1-fiber with non-A^1 generic
fibers.  Only if all dodge does the positive recognition program (fibrations,
Cl, Makar-Limanov, kappa-bar) begin.

Run: python3 candidate_sigma_prime.py
"""
import sympy as sp

x, y, z = sp.symbols('x y z')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')

# factorization of A (the trap-dodge mechanism)
assert sp.factor(A) == (x*y + 1)*(x**2*y**2*z + 3*x*y**3 + 2*x*y*z + 4*y**2 + z)
print("A = u * (u^2 z + y^2(4+3xy))  OK")

# Jelonek set at a=0 is b^2(bc-1): meets L_P in finitely many points only
Lam_star = 27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2
assert sp.factor(Lam_star.subs(a, 0)) == b**2*(b*c - 1)
print("Lam*|a=0 = b^2(bc-1): parabola L_P not inside the Jelonek set  OK")

# Z1-component of F^{-1}(L_P) at delta=1: explicit C*
G = C + 4*B**2 - 1
z1 = sp.solve(sp.Eq(sp.expand(G.subs(x, -1/y)*y**3), 0), z)
assert len(z1) == 1 and sp.expand(z1[0]) == -16*y**5 + y**3 + 5*y**2
print("Z1 = {x=-1/y, z=-16y^5+y^3+5y^2} iso C*  OK")

# Sigma' = {A o F = 1}: irreducible degree 43
At = (1 + a*b)**3*c + b**2*(1 + a*b)*(4 + 3*a*b)
AF = sp.expand(At.subs({a: A, b: B, c: C}, simultaneous=True))
assert sp.total_degree(AF, x, y, z) == 43
fl = sp.factor_list(AF - 1)
assert len(fl[1]) == 1 and fl[1][0][1] == 1
print("Sigma' = {A o F = 1}: irreducible, degree 43, smooth (etale preimage)  OK")
print("Sigma' iso A^2  <=>  JC(2) false; no known obstruction applies.")
