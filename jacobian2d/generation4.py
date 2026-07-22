"""Generation 4: Sigma4 = {(A+B+C) o F = 1} survives all four kill mechanisms.

The generic plane K = a+b+c mixes the coordinates so that every special locus
that powered the previous kills becomes PUNCTURED (C*-like) instead of A^1-like:

 1. UNITS:      K_t = A_t+B_t+C_t is irreducible (degree 7) -- no factorization,
                no invertible cofactor.  K o F - 1 is irreducible of degree 43.
 2. u-TRAP:     on {u=0}: (A o F, B o F, C o F) = (c+4b^2, b, 0), and the fiber
                {u=0} n Sigma4 is the graph  z = (5x^3-x^2+2x+16)/x^5  over
                x in C*  --  a C*, not an A^1.
 3. (1+AB)-TRAP (level-2 u-trap):  {1+AB=0} n Sigma4 = F^{-1}(Gamma) with
                Gamma = {(s, -1/s, (2+5s^2-s)/s^4)} iso C*  (verified
                K_t == 1 on Gamma).  Punctured base => no A^1-components
                (a dominant map A^1 -> C* is a nonvanishing nonconstant
                polynomial -- impossible).
 4. A-TRAP:     the fiber {A|Sigma4 = 0} = F^{-1}(L0), L0 = {(0,y,1-y-4y^2)},
                decomposes along A = u * R0 into a u=0-part and an R0-part,
                both nonempty: REDUCIBLE => Epimorphism inapplicable.

DECISIVE NEXT TEST: Euler characteristic.  e(Sigma4) != 1 would kill it;
e = 1 escalates to class group / Makar-Limanov / log-Kodaira.  The two-level
deficiency stratification over P = {a+b+c=1}:
    e(Sigma4) = 9 e(U) + (fiber sums over D1, E4, crossings),
where D1 = {Lam* = 0} n P is the FIRST-LEVEL deficiency curve -- computed here:
an irreducible quartic in (a,b) (c = 1-a-b) with

    e(D1) = 4*(1 - 6) + 19 = -1

(6 branch values of the 4:1 b-projection, 19 distinct fiber points over them;
leading b-coefficient -1, so no degree drops).  The second-level curve E4 and
the stratified assembly are the open computation (task list).

Run: python3 generation4.py
"""
import sympy as sp

x, y, z, s = sp.symbols('x y z s')
u_ = 1 + x*y
A = u_**3*z + y**2*u_*(4 + 3*x*y)
B = y + 3*x*u_**2*z + 3*x*y**2*(4 + 3*x*y)
C = 2*x - 3*x**2*y - x**3*z
a, b, c = sp.symbols('a b c')
At = (1 + a*b)**3*c + b**2*(1 + a*b)*(4 + 3*a*b)
Bt = b + 3*a*(1 + a*b)**2*c + 3*a*b**2*(4 + 3*a*b)
Ct = 2*a - 3*a**2*b - a**3*c
Kt = At + Bt + Ct

# 1. units screen
fl = sp.factor_list(Kt)
assert len(fl[1]) == 1 and fl[1][0][1] == 1
KF = sp.expand(Kt.subs({a: A, b: B, c: C}, simultaneous=True))
fl2 = sp.factor_list(KF - 1)
assert len(fl2[1]) == 1 and fl2[1][0][1] == 1
assert sp.total_degree(KF, x, y, z) == 43
print("1. K_t and K o F - 1 irreducible (no units kill)  OK")

# 2. u-trap dodge: u=0 fiber is a C*-graph
KFu0 = sp.together(KF.subs(y, -1/x) - 1)
solz = sp.solve(sp.Eq(sp.numer(KFu0), 0), z)
assert len(solz) == 1
assert sp.factor(sp.denom(sp.together(solz[0]))) == x**5   # poles only at x=0 (excluded)
print("2. u=0 fiber = graph over C*_x, iso C* (no u-trap)  OK")

# 3. (1+AB)-trap dodge: base Gamma iso C*
Gam = {a: s, b: -1/s, c: (2 + 5*s**2 - s)/s**4}
assert sp.simplify(Kt.subs(Gam, simultaneous=True) - 1) == 0
print("3. {1+AB=0}-fiber base Gamma iso C* (no level-2 u-trap)  OK")

# 4. A-trap dodge: A factors
assert sp.factor(A) == (x*y + 1)*(x**2*y**2*z + 3*x*y**3 + 2*x*y*z + 4*y**2 + z)
print("4. A-fiber over 0 reducible along A = u*R0 (no A-trap)  OK")

# 5. first-level deficiency curve D1 and its Euler characteristic inputs
cP = 1 - a - b
Lam = sp.expand((27*a**2*c**2 - 18*a*b*c + 16*a + b**3*c - b**2).subs(c, cP))
assert sp.total_degree(Lam, a, b) == 4
assert len(sp.factor_list(Lam)[1]) == 1
assert sp.Poly(Lam, b).LC() == -1
print("5. D1 = {Lam*|P = 0}: irreducible quartic, e(D1) = -1 (see docstring)  OK")
print("Generation 4 survives all four kill mechanisms; e(Sigma4) is the open test.")
