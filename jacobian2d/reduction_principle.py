"""The reduction principle: the 3D counterexample IS a 2D map with a square defect.

Every C^*-equivariant map of the counterexample's shape,
    F = ( alpha(w,t)/x^2 , beta(w,t)/x , x*gamma(w,t) ),   w = x*y, t = x^2*z,
induces a polynomial map on the invariant rings
    G(w,t) = ( alpha*gamma^2 , beta*gamma )        ( = (A C^2, B C) )
and the Jacobians are related by the IDENTITY

    det JF = det JG / gamma^2.

So a 3D equivariant Keller map is EXACTLY a 2D polynomial map G whose Jacobian
determinant equals  c * gamma^2  for a factorization G = (alpha*gamma^2, beta*gamma).
The C^*-fiber absorbs the square defect.  A genuine 2D counterexample needs
defect exponent ZERO, which this mechanism cannot produce (see REPORT.md).

Run: python3 reduction_principle.py
"""
import sympy as sp

x, y, z, w, t = sp.symbols('x y z w t')

# ---- 1. the identity, for generic alpha, beta, gamma -------------------------
al = sp.Function('alpha')(w, t)
be = sp.Function('beta')(w, t)
ga = sp.Function('gamma')(w, t)
sub = {w: x*y, t: x**2*z}
F = ((al/x**2).subs(sub), (be/x).subs(sub), (x*ga).subs(sub))
JF = sp.Matrix([[sp.diff(f, v) for v in (x, y, z)] for f in F]).det()
G1, G2 = al*ga**2, be*ga
JG = sp.diff(G1, w)*sp.diff(G2, t) - sp.diff(G1, t)*sp.diff(G2, w)
assert sp.simplify(JF - (JG/ga**2).subs(sub)) == 0
print("identity det JF = det JG / gamma^2   OK (generic alpha,beta,gamma)")

# ---- 2. the compressed map of the announced counterexample -------------------
u = 1 + w
alpha = u**3*t + w**2*u*(4 + 3*w)
beta = w + 3*u**2*t + 3*w**2*(4 + 3*w)
gamma = 2 - 3*w - t
G1 = sp.expand(alpha*gamma**2)
G2 = sp.expand(beta*gamma)
detG = sp.factor(sp.diff(G1, w)*sp.diff(G2, t) - sp.diff(G1, t)*sp.diff(G2, w))
print("compressed map of the announced example:  det JG =", detG)
assert detG == -2*(t + 3*w - 2)**2          # = -2*gamma^2
# G is a generically 3:1 polynomial self-map of C^2, Keller OFF the curve gamma=0.
Ab, Bb = sp.symbols('Abar Bbar')
fib = sp.factor(sp.resultant(G1 - Ab, G2 - Bb, t))
print("fiber equation (t eliminated), degree in w:",
      sp.degree(sp.expand(fib), w))
print()
print("The defect divisor {gamma=0} is intrinsic: composing with polynomial")
print("automorphisms multiplies det J by nonzero constants only, so no")
print("composition can cancel the zero locus of det JG.  Absorbing it requires")
print("an extra fiber direction -- i.e. dimension 3.")
