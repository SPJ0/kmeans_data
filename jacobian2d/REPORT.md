# Toward a two-dimensional counterexample to the Jacobian conjecture: a construction campaign

**Date:** 2026-07-21.
**Context:** On 2026-07-20 Levent Alpöge announced an explicit counterexample to the
Jacobian conjecture in dimension 3 (example produced by an AI model, question posed by
Akhil Mathew). The two-dimensional case remains open. This report documents a
construction-driven investigation of whether the new technique — or any relative of it —
can be pushed down to dimension 2. All computations are reproducible from the scripts in
this directory.

**Bottom line.** No 2D counterexample was found. But the investigation isolates *exactly*
where the 3D mechanism lives and proves, in several precise senses, that it cannot
compress to 2D: the entire construction is equivalent to a 2D map whose Jacobian
determinant has a *square defect* `c·γ²` absorbed by an extra fiber direction, and every
2D-internal way of trying to reach defect zero funnels into a single unsolvable
obstruction equation `W − λ·v^a·W^k = c` (`a ≥ 1, k ≥ 2`). In 3D the same equation
acquires an extra variable and becomes solvable — that is the whole difference between
the dimensions. A specification sheet for what any successful 2D construction must
achieve is given at the end. As a byproduct, the structure equations derived here produce
a **new counterexample instance** in 3D (degrees (8,7,5), det = −2, generically 3:1),
distinct from the announced (7,6,4) map.

---

## 1. The verified 3D counterexample

With `u = 1 + xy`:

```
a = u³z + y²u(4+3xy)          (degree 7)
b = y + 3xu²z + 3xy²(4+3xy)   (degree 6)
c = 2x − 3x²y − x³z           (degree 4)
```

Verified (`verify_3d_counterexample.py`): `det J = −2` identically, and the three
distinct points `(0,0,−1/4)`, `(1,−3/2,13/2)`, `(−1,3/2,13/2)` all map to `(−1/4,0,0)`.
Keller and non-injective ⇒ JC(n) is false for all n ≥ 3 (adjoin identity coordinates).

**Structure.** The map is homogeneous for the hyperbolic ℂ\*-action with weights
`x:−1, y:1, z:2` (target weights `a:2, b:1, c:−1`). Writing the invariants
`w = xy`, `t = x²z`, every such map has the shape

```
F = ( α(w,t)/x² , β(w,t)/x , x·γ(w,t) )
```

with polynomiality conditions on α, β. For the announced map: `α = u³t + w²u(4+3w)`,
`β = 3u²t + w + 3w²(4+3w)`, `γ = (2−3w) − t` (all linear in `t`).

Geometrically (per the Secret Blogging Seminar discussion) the map is the restriction of
`π: ℙ¹ × Sym²(ℙ¹) → Sym³(ℙ¹)`, `(p,{q,r}) ↦ {p,q,r}`, after removing the ramification
divisor and the preimage of a hyperplane tangent to the twisted cubic; both sides become
𝔸³ and the restriction is étale and generically 3:1 (étale on 𝔸ⁿ ⇒ det J is a
nonvanishing polynomial ⇒ constant ⇒ Keller). Dimension 3 "threads the needle": the
divisor-class bookkeeping (`{(2,1),(1,1)}` unimodular) fails for the analogous
constructions in every other dimension.

## 2. The reduction principle: 3D counterexample = 2D map with a square defect

The target invariants are `AC²` and `BC`, so F induces the polynomial self-map of ℂ²

```
G(w,t) = ( α·γ² , β·γ ).
```

**Identity (verified for generic α, β, γ, `reduction_principle.py`):**

```
det J_F  =  det J_G / γ².
```

Consequences:

- A ℂ\*-equivariant 3D Keller map of this shape is *the same thing as* a 2D polynomial
  map `G = (αγ², βγ)` with `det J_G = c·γ²` — Keller **off the curve** `{γ = 0}`,
  with defect exactly a square supported on the fiber-compression divisor.
- For the announced map, `det J_G = −2γ²` and G is generically 3:1 — a genuinely
  non-injective, near-Keller self-map of ℂ². The fiber equation (resultant eliminating
  `t`) has degree 6 in `w`, containing the announced cubic `w²−w³ = ...` structure.
- The defect is **intrinsic**: pre/post-composing with polynomial automorphisms
  multiplies `det J` by nonzero constants, so no change of polynomial coordinates can
  cancel the zero divisor of `det J_G`. Zeros of Jacobians only accumulate under
  composition; only an extra fiber direction (dimension 3) can absorb them.

So the exact content of the 3D trick is: *manufacture a 2D near-Keller map whose defect
is a perfect square along one curve, then absorb that curve into a ℂ\*-fibration.* The 2D
problem demands defect zero, and the absorption device is unavailable.

## 3. Rigidity theorems: the 2D-internal routes die

### 3.1 Equivariant rigidity (the direct port is impossible)

For a hyperbolic ℂ\*-action on ℂ² with weights `x:−p, y:q` (`gcd(p,q)=1`), equivariant
components have the form `x^{a₁}y^{a₂}h(v)`, `v = x^q y^p`, and (verified formula,
`rigidity_2d.py`):

```
det J = x^{a₁+b₁−1} y^{a₂+b₂−1} · Φ(v),
Φ = (a₁b₂−a₂b₁)·hg + v[(qb₂−pb₁)h′g − (qa₂−pa₁)hg′].
```

Constant nonzero det forces `a₁+b₁ = a₂+b₂ = 1` and `Φ = c`; the coefficient of
`v^{H+G}` in Φ is `(1+qH+pG)·h_H·g_G ≠ 0` unless `H = G = 0`. Hence:

> **Theorem A.** Every Keller map of ℂ² equivariant under a hyperbolic ℂ\*-action is
> linear. (Since all ℂ\*-actions on 𝔸² are linearizable, no ℂ\*-symmetric 2D
> counterexample exists at all.)

The count that fails: in 2D the invariant space is 1-dimensional and the constant-det
condition is an overdetermined ODE in one variable; in 3D the invariant space is
2-dimensional, one PDE for three functions — underdetermined, with room for the seed.

### 3.2 Two-graded-piece relaxation: one obstruction equation, no solutions

Minimal relaxation: each component is a sum of two graded pieces. In the fully-coupled
symmetric sector `P = yᵐh₁ + xⁿh₂`, `Q = yⁿg₁ + xᵐg₂` (cross-weights zero), the graded
equations integrate exactly (all brackets are total derivatives in `v`) to

```
n·vⁿ·T − m·vᵐ·S = c·v,      S = h₁g₂,  T = h₂g₁,
```

with side conditions `h₁ⁿ ∝ g₁ᵐ`, `h₂ᵐ ∝ g₂ⁿ` from the extreme weight levels. Then:

- `m, n ≥ 2`: left side divisible by `v²`, right side isn't — **no solution**;
- `min(m,n) = 1` (say `m=1`): reduces to `W − λ·v^{n−1}·Wⁿ = −c` for `W = h₁ψ` —
  **no polynomial solution** (degree `nD+n−1 > D` for `n ≥ 2`);
- `m = n = 1`: forces `h₁h₂ = const` — **linear maps only**.

The only Keller maps in these sectors are de Jonquières automorphisms arising on branches
where a piece vanishes — confirmed by symbolic solve for (m,n) = (1,2), (1,3), (2,3)
(`rigidity_2d.py`; for (1,1), (2,2) the sympy solver is incomplete and misses even the
linear branches, but those cases are covered by the hand proof above).

### 3.3 Resonant three-piece sectors: the same funnel

Adding weight-0 pieces `h₀(v), g₀(v)` or a third graded piece opens "resonance channels"
(colliding bracket weights). Checked by hand:

- Non-resonant weight patterns: mixed brackets `[P_m, Q_0]` sit alone at their level and
  force `h₀, g₀` constant — reduces to the two-piece case.
- Parity-split patterns (P even weights, Q odd): the weight-0 level receives no cross
  terms at all ⇒ `c = 0` — dead on arrival.
- Arithmetic-progression resonance `{2,0,−2} × {2,0,−2}`: the cascade forces either
  `h₀` constant (reduction) or `Q = e·P + const` (det ≡ 0) — dead.
- `{3,0,−1} × {1,0,−3}` (two genuine channels at level 0): integrates to
  `W − 3τσ·v²·W³ = c` — the same obstruction shape, **no solutions**.
- Non-scalar proportionality sector `(m,n) = (2,4)`: level-0 condition
  `4v⁴S₂ − 2v²S₁ = cv` — `v²`-divisibility kill again.

> **Unified obstruction.** Every structured 2D sector examined collapses to
> `W − λ·v^a·W^k = c` with `a ≥ 1, k ≥ 2` (no polynomial solutions), to a
> divisibility contradiction, or to a degeneration. To get the solvable `a = 0` shape one
> needs a cross-pair with unit monomial prefactor, which forces weight ±1 pieces and
> lands back in the dead `(1,n)` case.

**The 3D contrast, made exact.** Running the identical procedure in 3D
(`family_3d.py`) — ansatz `γ = g(w)−t`, `β = 3u²t+b₀(w)`, `α = u³t+a₀(w)` — the
constant-det condition becomes three ODEs whose *first* is the same proportionality
(`a₁² ∝ b₁³`), but the remaining two equations involve three free functions:
underdetermined. Solving yields a family with free parameters `G0, G2` and
`det J = −G0²/2`:

- `G0=2, G2=0`: the announced map, degrees (7,6,4);
- `G0=2, G2=1`: a **new counterexample**, degrees (8,7,5), `det J = −2`, generic fiber
  of 3 points (verified). The extra invariant `t` is precisely the variable that turns
  the unsolvable 2D functional equation into a solvable linear system.

### 3.4 Laurent solvability: the boundary of the obstruction

The obstruction `W − λv^aW^k = c` *is* solvable in Laurent polynomials
(valuation `ν = −a/(k−1)` balances the degrees). Allowing poles on `{v = xy = 0}`
means working on 𝔸¹×𝔸\* instead of 𝔸² — and indeed étale non-injective self-covers of
𝔸¹×𝔸\* exist trivially. The 2D Jacobian conjecture is exactly the statement that the
rigidity of 𝔸² (no nonconstant units) blocks this. The obstruction equation and the
units/topology obstructions are two faces of the same coin.

## 4. The geometric (étale) template in 2D

The 3D construction fits the template: finite d:1 map of projective varieties
`π: X → Y`, remove divisors so both sides become 𝔸ⁿ and π becomes étale but non-proper.
Ported to surfaces:

- **Degree 2 is impossible — full proof.** For a 2:1 finite cover, the fiber over any
  branch point is a single ramified point. An étale restriction must remove all
  ramification, so the branch curve `B ⊂ 𝔸²` is missed entirely by the image. Its
  equation `f_B` then pulls back to a nowhere-zero polynomial on the source 𝔸², hence a
  constant — forcing `B = ∅`, so the cover is proper étale over simply connected 𝔸²,
  hence trivial. (Via Stein factorization this kills geometric degree 2 for *any* 2D
  Keller map, not just template constructions. For d ≥ 3 the argument fails exactly
  because fibers over branch points can contain unramified points — the loophole the 3D
  example exploits.)
- **Sym² analogue computed exactly.** `π: ℙ¹×ℙ¹ → Sym²ℙ¹ = ℙ²`, branch conic
  `s² = 4p`; the tangent lines to the conic are the pencils "pairs containing a fixed
  point", whose preimages split as `(1,0)+(0,1)` rulings meeting on the diagonal —
  precisely the divisor-class bookkeeping needed to kill Pic. Removing
  `Δ ∪ {0}×ℙ¹ ∪ ℙ¹×{0}` gives source `{(q′,r′) ∈ 𝔸² : q′ ≠ r′} ≅ 𝔸¹×𝔸*` — **not**
  𝔸² (nonconstant unit `q′−r′`), and the map is just the elementary symmetric map off
  the diagonal. The `d = 2` needle cannot be threaded, in agreement with the proof above.
- **Self-maps of ℙ² are dead.** `Y∖D_Y ≅ 𝔸²` forces `D_Y` to be a line; `π⁻¹(line)`
  has degree d, so the source complement is 𝔸² only if `π⁻¹(L)` is a d-fold line — but
  then the restriction is finite (proper) and étale over 𝔸², hence trivial.
- **Known bounds.** Any 2D Keller counterexample has algebraic degree > 100
  ([Moh](https://matwbn.icm.edu.pl/ksiazki/bcp/bcp31/bcp31116.pdf)) and geometric degree
  ≥ 5 by Orevkov (3-sheeted) and
  [Domrina–Orevkov (4-sheeted)](https://link.springer.com/article/10.1007/s13366-014-0208-4),
  since extended to 5-sheeted — so ≥ 6. Any "fixed curve ∩ line" fiber mechanism in 2D
  must produce fibers of degree ≥ 6 while keeping *every* local branch structure
  nontrivial. The 3D example needed none of this: its fiber degree is 3.

## 5. Probing the new 3D family for 2D shadows

- **Invariant plane.** Every member of the family maps `{x=0}` to `{C=0}` and the
  restriction is *always* `(y,z) ↦ (z + κy², B₁y)` — a triangular automorphism. The
  non-injectivity provably never lives on the degenerate fiber plane.
- **Slices and projections.** `x=1` slices projected to coordinate pairs have
  non-constant Jacobians with no absorbable structure (e.g. `(a,b)`-projection defect
  `(y+1)²·(cubic)`).
- **𝔾ₐ versus 𝔾ₘ (the exact gap).** A 3D Keller map equivariant for a *translation*
  action — i.e. of the form `(x + f(y,z), g(y,z), h(y,z))` — has
  `det J = det J_{(g,h)}`, so a non-injective one **is equivalent to a 2D
  counterexample**. The new counterexamples are 𝔾ₘ-fibered instead, and Theorem A +
  the defect analysis explain why the 𝔾ₘ-quotient cannot be traded for a 𝔾ₐ-quotient:
  the ℂ\*-torsor twisting is what absorbs `γ²`, and 𝔸¹-fibrations of 𝔸² admit no such
  twisting (Keller maps preserving an 𝔸¹-fibration are de Jonquières). JC(2) is
  *exactly* the statement that the 3-to-1 phenomenon cannot live over a 𝔾ₐ-quotient.

## 6. Specification sheet for any future 2D counterexample

Any 2D Keller counterexample must simultaneously:

1. have algebraic degree > 100 and geometric degree ≥ 6;
2. admit **no** ℂ\*-symmetry (Theorem A) and preserve **no** 𝔸¹-fibration;
3. have a Newton polygon not reducible to ≤ 2 graded pieces in any hyperbolic grading
   (§3.2–3.3), i.e. genuinely "fat" support surviving the Abhyankar–Moh cascade;
4. as an étale endomorphism, have a nonempty branch curve on which *every* fiber contains
   at least one unramified point (§4, degree-2 argument), with the source compactifying
   to a surface whose boundary bookkeeping kills both Pic *and* units — the step that
   failed at `𝔸¹×𝔸*` in every attempt here;
5. produce its non-injectivity by a mechanism other than fibration-absorption of a
   Jacobian defect (§2: defects only accumulate under composition in fixed dimension).

Constructions not yet exhausted by this campaign, in order of assessed promise:
(a) covers `X → Y` between *different* rational surfaces (Hirzebruch/blown-up ℙ²)
with d ≥ 6 and non-reduced boundary trades — the class-group unimodularity condition
has many more degrees of freedom than the Sym family probed here; (b) resonant sectors
with ≥ 4 graded pieces, where the funnel argument of §3.3 has not been closed by hand
and cancellations between *three* level-0 channels are combinatorially possible;
(c) positive-characteristic-inspired lifts (Frobenius-like kernels have no char-0
analogue on 𝔾ₐ², but twisted forms over function fields were not examined).

## 7. Phase 2: the live candidates — Borisov's frameworks beyond Moh's barrier

Following the specification sheet, the second phase attacked the only known *positive*
program for 2D: Borisov's frameworks (Electron. J. Combin. 27 (2020) #P3.54) — explicit
combinatorial data (dual graphs at infinity of source/target compactifications, Picard
pushforward/pullback, ramification bookkeeping) satisfying **all** known numerical
obstructions, such that "each framework corresponds to a large system of equations,
whose solution would lead to a Keller map."

**The landscape, extracted from the paper:**

- **First framework:** geometric degree 16, polynomial degrees (99,66) — the *last
  troublesome case* of Moh's degree-≤100 theorem. Borisov's Remark 3 documents that
  Moh's published discard of this case is a sketch; Yansong Xu claimed a gap (his patch
  had its own acknowledged error); Horruitiner's Master's thesis and Borisov's own Maple
  computation both conclude "no map" — but "we currently do not have a simple reason",
  and Borisov explicitly distrusts single-source bookkeeping at this scale.
- **Isotope family (k = 2..6):** same target graph, degree pairs
  **(99,66), (135,90), (171,114), (207,138), (243,162)**. Everything with k ≥ 3 lies
  beyond Moh's theorem and is **completely open**. The k=3 framework, degrees (135,90),
  geometric degree 16, is the minimal live candidate for a 2D counterexample.
- **Second framework:** geometric degree 28, degrees (435,290) — open.
- **Three-dessin framework:** no type-4 curves — open.

**Borisov's near-miss and the defect connection.** For the first framework Borisov
exhibits an explicit generically-16:1 polynomial map built from a degree-16 Belyi map
(`y₁ = x₁³x₂⁸·p(w̃)`, `y₂ = x₁²x₂⁵(x₁x₂³−1)·r(w̃)`, `w̃ = (x₁x₂³−1)³/x₂`) whose
Jacobian is `const·x₁⁴x₂¹²` — a pure **monomial defect**, the exact 2D analogue of the
compressed map G of §2 (defect `−2γ²`). He remarks it cannot be repaired "even by
introducing additional variables" — written in 2020. The 2026 counterexample shows
defect absorption by additional variables *is* possible in dimension 3; whether Borisov's
16:1 near-miss defect `x₁⁴x₂¹²` is absorbable into a 3D/4D Keller map is a new question
this connection raises (it would give counterexamples of a second, Belyi-powered type).

**The Belyi engines, constructed.** The frameworks are powered by Belyi maps on the two
forked boundary curves. The isotope family needs:

- on the (−5)-curve (shared by all isotopes): degree 16, profile
  `(0:[2⁸], ∞:[3⁵,1], 1:[13,1³])`. **Constructed exactly over ℚ(√−3)**
  (`belyi16_exact.py`), via a chain of identities that unifies everything in this
  report:
  * For the near-miss ansatz `y₁ = x₁³x₂⁸p(W̃)`, `y₂ = x₁²x₂⁵(x₁x₂³−1)r(W̃)` with
    *arbitrary* p (deg 8), r (deg 5): **det J = x₁⁴x₂¹²·Φ(W̃)** where
    `Φ = pr + W(3pr′ − 2p′r)` — the graded Φ-equation of §3.1, in the resonant
    sector where the leading obstruction `1 + 3·deg r − 2·deg p = 0` vanishes. The
    monomial defect is exactly the graded prefactor of the §3.1 formula: near-misses
    are resonant graded pairs, true Keller would need prefactor 1 (the dead sectors).
  * `Φ = c` (constant) ⟺ `T(w) := w·r³/p²` satisfies `T′ = c·r²/p³` ⟺ T is the
    degree-16 Belyi map: zeros give [3⁵,1], poles [2⁸], and `T−1 ~ −(c/13)w⁻¹³` at
    ∞ gives the 13-point, with `w·r³ − p² = cubic` supplying the three simple points.
  * Solving `Φ = c` (bilinear; r eliminates linearly; Groebner on 7 conditions in p):
    exactly one non-degenerate component — the other is the degenerate family
    `p = w²q³, r = wq², Φ ≡ 0` — giving a **unique solution up to the choice of
    √−3**: `p₆ = 12151/28812 + (81/4802)√−3` etc. (full closed form in
    `belyi16_exact.py`). The two Galois-conjugate solutions match the combinatorial
    dessin count **156/78 = 2** (`belyi_deg16.py`).
  * With this exact pair, **Borisov's near-miss is reconstructed and verified
    exactly**: a polynomial map of degrees (99,66) with `det J = c·x₁⁴x₂¹²`,
    c ≠ 0 ∈ ℚ(√−3) — the closest known object to a 2D Keller map, now in closed form.
- on the (−2)-curve of the k=3 isotope: degree 13, profile
  `(∞:[13], 0:[3,3,3,1,1,1,1], 1:[7,1⁶])`. **Constructed explicitly**
  (`belyi_k3.py`): writing `g = A³B` with the 7-fold point at 0 forces
  `g′ = 13t⁶A²`, `g(0)=1`, and the single condition `A³ | g` gives 9 equations in the 3
  coefficients of A. The Groebner basis is triangular over a degree-65 polynomial that
  is a **quintic in a₂¹³** (the 13th roots of unity are the residual scaling); the
  quintic is irreducible over ℚ — the dessin's moduli field has degree 5, matching the
  count of admissible plane trees. A real solution was extracted to 40 digits and the
  full profile verified (7-fold root exact, A, B, D squarefree and coprime).

**Non-absorbability of the near-miss (checked).** Under the torus weights (3,−1) the
invariant of Borisov's near-miss is `v = x₁x₂³` and the defect is `c·v⁴`; the
compression-absorption patterns of §2 (generalized to weights `(a,b,e)`) all require
`γ^{a/e} | y₁`, `γ^{b/e} | y₂` for the defect root γ, and every admissible pattern fails
on the monomial exponents `(x₁³x₂⁸, x₁²x₂⁵)`. So the near-miss is *not* the compression
of an equivariant 3D Keller map — an independent confirmation of Borisov's remark, and a
sharper one: under the (3,−1) grading the near-miss spreads over ~9 graded pieces. The
frameworks thus live exactly beyond the 2–3-piece sectors closed in §3, at a graded
depth where only Borisov's k=2 machine computation has ever closed the cascade.

**What remains for a full realization of the k=3 candidate** (the concrete route to a 2D
counterexample, after Borisov's method for k=2): write `y₁, y₂` as Laurent polynomials in
the edge coordinates `(v, w)` of the source graph with Newton polygon fixed by the
framework (vertices at (0,0), (3,0), (36,99)-type data, ~thousands of coefficients),
impose the pole orders of the framework at every boundary curve, seed the leading
behavior along the forked curves with the two Belyi maps above, and solve the resulting
system — linear in the y-coefficients, nonlinear in a handful of moduli parameters e_i.
For k=2 Borisov reduced hundreds of equations to "a dozen or so coefficients" before
finding an incompatibility; there is no computation on record for k ≥ 3, and the k=3
system is now partially seeded by the explicit Belyi data above. This is where the
2D question currently lives: either the k=3 cascade closes (automorphism-style collapse,
extending the pattern of §3), or its solution is the first 2D Keller map.

## 8. Contrarian route: the 3D map as an engine — interpolating multisections

No one can have searched this region before 2026-07-20: it needs the explicit 3D map
as raw material (`multisection_2d.py`).

**Reformulation (non-injectivity for free).** Let `p₂ = (1,−3/2,13/2)`,
`p₃ = (−1,3/2,13/2)` (marked points with `F(p₂) = F(p₃)`). For *any* polynomial map
`φ: ℂ² → ℂ³` — no embedding, no étaleness — set `g = (A∘φ, B∘φ)`. If φ interpolates
`φ(q₂) = p₂`, `φ(q₃) = p₃` then `g(q₂) = g(q₃)` automatically, and

> **JC(2) is false ⟺ some interpolating φ satisfies the single PDE
> `φ*(dA∧dB) = c·ds∧dt`, c ≠ 0** (⟸ direction; the classical hard part —
> non-injectivity — is built in, and all difficulty moves into a soft-looking
> constant-area condition on a surface parametrization).

Facts established:

- The trivial section `φ₀ = (0,s,t)` solves the PDE (`det = −1`, injective); affine
  interpolating planes admit only degenerate (`det ≡ 0`) solutions.
- **μ₂-equivariant sector.** `p₂, p₃` are swapped by the ℂ\*-action at `λ = −1`.
  Full ℂ\*-equivariance of φ is forbidden (it would make g equivariant, hence linear by
  Theorem A), but ℤ/2-equivariance `φ∘(−s,t) = (−x,−y,z)∘φ` is *not*: interpolation at
  one point suffices. Parity kills the `(B,C)`-projection (det forced odd ⇒ c = 0);
  `(A,B)` and `(A,C)` survive. Degrees 1–2: no solutions — consistent with Moh, which
  requires `deg φ ≥ 15` for any success. Equivariant JC(2) for *finite* groups appears
  to be untouched territory.
- **The collision leaf.** `{B=C=0} = 𝔸¹ ⊔ ℂ*`: the z-axis with `A = z` (bijective
  section sheet) and `{(x, −3/(2x), 13/(2x²))}` with **`A = −1/(4x²)`** — an étale
  double cover of `ℂ∖{0}` whose deck transformation is exactly `x ↦ −x`. Fibers:
  `1+2` over `a ≠ 0`, `1` over the escape value `a = 0`; the triple collision at
  `a = −1/4` is the section point plus the μ₂-pair `x = ±1`. The **1D germ** of the
  counterexample is `𝔸¹ ⊔ ℂ* → 𝔸¹`, `(z,x) ↦ (z, −1/(4x²))` — étale and non-injective
  *because it is powered by a unit*. JC(2) asks whether the ℂ*-sheet can be thickened
  to an 𝔸²-sheet; 𝔸² has only constant units — the same rigidity every route hits,
  now localized on one explicit curve.
- **No infinitesimal obstruction.** The linearization of the PDE at φ₀ is
  `L(δ) = −div(δ₂,δ₃) − 3s·δ₁ − (12s²+3t)∂ₛδ₁ + (89s³+21st)∂ₜδ₁`, **surjective on
  polynomials** (every polynomial is a divergence): any transverse motion δ₁ — the
  direction that must reach `x = ±1` — can be compensated at every order. The
  deformation theory is completely flexible; the entire content of JC(2) here is a
  *global degree-finiteness* question (do the order-by-order corrections resum to a
  polynomial of finite degree?).
- **Consistency box.** An embedded bisection would be a geometric-degree-2 Keller map
  (impossible, §4); a trisection is killed by Orevkov. So a successful multisection must
  cut generic `(A,B)`-leaves ≥ 6 times while interpolating the marked μ₂-pair — sharp,
  previously unformulated targets for a construction.

## 9. Iterated Keller preimages: the surface Σ, a live 𝔸² candidate at 9 sheets

The sharpest new object of the campaign (`iterated_preimage.py`). The surface
`S₁ = {B=0} = F⁻¹(plane)` carries a 3:1 étale map `(A,C)|S₁ → 𝔸²`, so **Orevkov's
theorem forces S₁ ≇ 𝔸²**. But `H = F∘F` is a 9-sheeted 3D Keller map, and 9-sheeted 2D
Keller maps are beyond every known exclusion (3: Orevkov, 4: Domrina–Orevkov, 5:
extensions). Therefore

```
Σ = {B∘F = 0} = H⁻¹(plane),   9:1 étale over 𝔸²,
```

is **not forbidden** from being 𝔸². Established facts:

- `B∘F` is **irreducible of degree 37**; Σ is a smooth irreducible affine hypersurface
  (smoothness: étale preimage of a plane).
- **Fiber machinery.** Over target `(a,b,c)` the x-coordinates of `F⁻¹(a,b,c)` are the
  valid roots of the cubic `Λ*·x³ + (4−3bc)x − 2c` with
  `Λ* = 27a²c² − 18abc + 16a + b³c − b²` — so the Jelonek set of F is `{Λ* = 0}`.
  Over the plane `b=0`: `ψ = a(27ac²+16)x³ + 4x − 2c`, discriminant
  `−4Λ(27ac²+8)²`; at the marked target `(−1/4, 0)`: `ψ = −4x(x−1)(x+1)` — the three
  collision x-coordinates. The squared discriminant factor is a fake collision (two
  sheets share x, differ in (y,z)); the genuine deficiency strata are `{a=0}` (fiber 1)
  and the ℂ\*-curve `{27ac²+16=0}` (fiber 1).
- **Euler characteristic of S₁ via the ℂ\*-action.** F *is* equivariant, so fiber
  counts are constant on ℂ\*-orbits of the (a,c)-plane; every 1-dimensional orbit is a
  ℂ\* with `e = 0`, hence `e(S₁) = #(fiber over the origin) = #F⁻¹(0) = 1` — confirmed
  by an independent stratified count `3·0 + 1·1 + 1·0 = 1`.
- **Correction (important).** `H = F∘F` is **not** ℂ\*-equivariant — F's target weights
  `(2,1,−1)` differ from its source weights `(−1,1,2)` — so Σ is *not* ℂ\*-stable
  (`B∘F` splits into graded pieces of weights differing by 3) and the orbit argument
  does **not** apply to Σ. An earlier version of this section claimed `e(Σ) = 1`; that
  claim is withdrawn. **`e(Σ)` is currently open**: it requires the second-layer
  deficiency curve `E = (A,C)(S₁ ∩ {Λ*=0})` and the stratified count
  `e(Σ) = 9·e(U) + 3·e(L₁°) + 3·e(Q°) + 7·e(E°) + (point corrections)`.
- Generic fibers of the 9:1 map were verified numerically (Newton-refined) at two
  generic targets: exactly 9 points. Over the marked target the fiber is
  `1+3+3 = 7` points exactly — the intermediate `p₁ = (0,0,−1/4)` lies *on* the
  Jelonek set (`Λ*(p₁) = 0`, single preimage `(−1/8,0,0)`), while `p₂, p₃` are off it.
  The 9:1 map on Σ has abundant built-in collisions.
- **The deficiency curve E is computed** (`E_curve.txt`): eliminating (y, x) from
  `{N_B, N_A, N_Λ}` via resultants gives `res_x(ψ̂, U) = c¹²·E·E'`, where E has
  (a,c)-bidegree (14,11) (total degree 24, 28 monomials) and E′ bidegree (14,25).
  Sampling fibers on each: on E the 9:1 map drops to **7** (genuine second-layer
  deficiency: one intermediate point crosses the Jelonek surface), on E′ it stays 9
  (spurious factor).

### 9.1 Resolution of the dichotomy: Σ ≇ 𝔸² (the AMS/Epimorphism obstruction)

The dichotomy is **decided — negatively — by a new mechanism** (`ams_obstruction.py`),
independent of Orevkov's theorem and effective at *any* sheet number.

**The obstruction.** The Abhyankar–Moh Epimorphism Theorem: if `f ∈ ℂ[s,t]` has a
scheme fiber that is a reduced irreducible 𝔸¹ (`ℂ[s,t]/(f) ≅ ℂ[T]`), then f is a
coordinate — so *all* its fibers are reduced 𝔸¹'s. Hence a smooth affine surface
carrying a regular function with one reduced 𝔸¹-fiber and one non-𝔸¹ fiber cannot
be 𝔸².

- **S₁ ≇ 𝔸², Orevkov-free.** The function x on S₁ has fibers ≅ ℂ* for x ≠ 0 (the
  z-graph has a genuine pole at `y = −1/λ`, numerator −2/λ) and the *reduced z-axis*
  (≅ 𝔸¹) over x = 0 (`B(0,y,z) = y`). AMS kills planarity.
- **Every level set {B=c} ≇ 𝔸²** — same fibration, with a second 𝔸¹-fiber at
  `x = 2/c` where the pole cancels.
- **Σ ≇ 𝔸².** The z-axis lies *inside the Jelonek set* of F (`Λ*(0,0,t) = 0`), with
  single-point fibers `F⁻¹(0,0,t) = {(t/2,0,0)}` — so the zero fiber of `A|Σ` is
  exactly the **x-axis**, and along the whole axis `dA = (0,0,1)`,
  `d(B∘F) = (0,1,9x)` have constant minor −1: the fiber is smooth of multiplicity
  one, a reduced irreducible 𝔸¹. Generic fibers of `A|Σ` are étale ≤3:1 covers of
  punctured ℂ*'s — no component can be 𝔸¹ (an étale dominant map 𝔸¹ → ℂ* is a
  nonvanishing polynomial with nonvanishing derivative: impossible). AMS closes it.

**Moral: the Jelonek set is the enemy.** Deficiency loci in the target whose fibers
drop to single points pull back to reduced 𝔸¹-fibers inside preimage surfaces, and AMS
turns those into exoticity certificates. Any future iterated-preimage construction must
arrange the deficient fibers to be *empty* (full escape) rather than singletons.

**Byproduct.** S₁, {B=c}, Σ form an explicit family of smooth affine surfaces with
trivial units, `Cl = 0`, `e(S₁) = 1`, `π₁(S₁) = 1` — plane-like in every classical
invariant — that are *not* 𝔸²: exotic-plane-type surfaces canonically attached to the
Jacobian counterexample, with κ̄ ∈ {0,1} forced (an 𝔸¹-fibration would trigger
Miyanishi–Sugie ⇒ 𝔸²).

### 9.2 Second generation: Σ′ = {A∘F = 1} dodges the trap (`candidate_sigma_prime.py`)

Classifying first-level planes by their trap status: `{b=const}` → AMS trap (singleton
Jelonek fibers over the z-axis — checked *family-wide*: the (8,7,5) instance collapses
identically, forced by `w² | a₀`, `w | b₀`); `{c=const}` → units obstruction
(≅ ℂ*×𝔸¹); but **`{a=δ}`, δ ≠ 0 escapes**: the x=0 fiber of `S_P` is the parabola
`L_P = {(0,y,δ−4y²)}`, which meets the Jelonek set (`Λ*|_{a=0} = b²(bc−1)`) in only
finitely many points — fibers over `L_P` are generically 3 points, not singletons. And
the would-be trap function's zero fiber `F⁻¹(L_P)` is **reducible** — since
`A = u·(u²z + y²(4+3xy))`, it splits as a ℂ*-component
`{x = −1/y, z = −16y⁵+y³+5y²}` plus a bidegree-(2,4) plane-curve component — and the
Epimorphism theorem requires an *irreducible* 𝔸¹-fiber. The known obstruction fails
structurally.

> **New live candidate: Σ′ = {A∘F = 1}** — irreducible of degree 43, smooth, carrying
> the 9:1 étale map `(B∘F, C∘F)` to `{a=1} ≅ 𝔸²`. **Σ′ ≅ 𝔸² ⟺ JC(2) is false**, and
> no known obstruction applies. Protocol before positive recognition tools: hunt for
> AMS traps among all natural functions on Σ′ (`B∘F`, `C∘F`, coordinates, `u`,
> low-degree combinations) — any reduced irreducible 𝔸¹-fiber with non-𝔸¹ generic
> fibers kills it; if all dodge, proceed to fibrations, `Cl`, Makar-Limanov, κ̄.

**Trap-hunt round 1: Σ′ survives everything** (`traphunt_sigma_prime.py`). The x=0
fiber is a punctured conic cover (disc `y⁴(y²+12)`); the u=0 fiber is ℂ* minus 3
points (poles `(2y³−1)³`); the y=0 and z=0 sections have monomial leading forms
(`−27x⁶z⁷`, `−59049x¹⁴y²²`) hence *two* places at infinity — never 𝔸¹. The `B∘F`
base curves are `x(y²−βy+3) + (y−β) = 0` ≅ 𝔸¹ minus the two roots of `q = y²−βy+3`
(the `(xy+1)²` resultant factor is spurious since `A=1` forces `u ≠ 0`), and the `C∘F`
base curves are **plane cubics** `−λ(1+v)³ + x(1+v)(v+2) − x³` in `(x, v=xy)` — genus
1 generically, punctured-rational when degenerate. In every case the unit argument (a
dominant map `𝔸¹ → line minus a point` is a nonvanishing nonconstant polynomial —
impossible) excludes 𝔸¹-components from all fibers, for **all** values of the
parameter.

**Meta-insight.** On Σ′ the equation `A∘F = 1` *activates the units* `u = 1+xy` and
`1+AB`: they are nonvanishing on Σ′, so every natural base curve is punctured, and
punctured bases cannot support 𝔸¹-fibers. The same unit-rigidity of 𝔸² that blocks
naive 2D constructions from below now *protects* the candidate from the AMS trap.

### 9.3 Correction and resolution: the units kill Σ′; the u-trap kills generation 3;
### complete classification of coordinate level-surfaces (`level_set_classification.py`)

**The "meta-insight" was the murder weapon.** The factorization
`A_t = (1+ab)·R`, `R = (1+ab)²c + b²(4+3ab)`, means that on `Σ′ = {A∘F = 1}` the
polynomial `1+AB` is *invertible* — its inverse is `R∘F` — and it is nonconstant on Σ′
(degree 13 < 43). **A nonconstant unit ⇒ Σ′ ≇ 𝔸².** The round-1 trap-hunt (§9.2)
missed the units screen, the simplest invariant of all; its fiber computations stand,
but its conclusion "no known obstruction applies" was wrong. The same kill applies to
every `{A∘F = δ}` (δ≠0) and — since `C_t = a(2−3ab−a²c)` factors — to every
`{C∘F = λ}` (λ≠0).

**Generation 3, `Σ″ = {B∘F = β}` (β≠0), dies by a new trap: the u-trap.** On `{u=0}`
the first coordinate `A = u·(…)` vanishes, so `B∘F|_{u=0} = B|_{u=0} = −2y`; hence
`{u=0} ∩ Σ″` is the *single reduced line* `{(2/β, −β/2, z)} ≅ 𝔸¹` (at β=1: chart
equation `x¹³(x−2)` with x≠0; the 2×2 minor of `(du | d(B∘F))` is constantly 1 along
the line). A generic u-fiber lives in `{xy = μ−1} ≅ ℂ*×𝔸¹`, where any 𝔸¹ must be a
vertical line (maps 𝔸¹→ℂ* are constant); at μ=2 the fiber is one irreducible
(12,6)-curve with no vertical factor — not 𝔸¹. Epimorphism ⇒ **Σ″ ≇ 𝔸²**.

> **Classification.** No level surface of any coordinate of `H = F∘F` is 𝔸²:
> `{A∘F = δ}` and `{C∘F = λ}` die by units; `{B∘F = 0}` by the axis-AMS trap (§9.1);
> `{B∘F = β}`, β≠0, by the u-trap. Three distinct kill mechanisms, all elementary
> once seen, none previously in the JC literature (they need the explicit F).

**Generation 4 opens: generic-plane level sets.** For `K = αa + βb + γc` with generic
coefficients, `{K∘F = δ}` dodges all three mechanisms: `K_t` does not factor (no unit
kill); on `{u=0}` the triple `(A∘F, B∘F, C∘F) = (c+4b², b, 0)` makes the u=0 fiber a
graph over `y ∈ ℂ*` — a ℂ*, not an 𝔸¹ (no u-trap); and the `{A=0}`-fiber decomposes
along `A = u·R₀` (reducible — no A-trap). The generation-4 recognition problem is
open, and the loop continues: each generation either dies by a sharper elementary
mechanism or survives one filter closer to being the counterexample.

**Dichotomy — either resolution is beyond current knowledge:**

> **Σ ≅ 𝔸² ⟺ JC(2) is false** (the 9:1 restriction is then an explicit 9-sheeted
> Keller counterexample). **Σ ≇ 𝔸²** requires a new Orevkov-type obstruction at 9
> sheets. And S₁ (irreducible, smooth, `e = 1`, non-𝔸² *only* because of Orevkov) is an
> exotic-plane candidate canonically attached to the counterexample.

The recognition problem for the explicit degree-37 hypersurface Σ is now the concrete
frontier: the next steps are its Makar-Limanov invariant / Derksen invariant, the
divisor class group of `ℂ[x,y,z]/(B∘F)`, and the DPD (Dolgachev–Pinkham–Demazure)
presentation of the hyperbolic ℂ\*-surface Σ — each computable in principle from the
explicit equation, and each capable of deciding the dichotomy.

### 9.4 Generation 4: the generic plane dodges the whole arsenal (`generation4.py`)

`Σ₄ = {(A+B+C)∘F = 1}` — irreducible, degree 43, smooth, 9:1 étale over
`P = {a+b+c=1} ≅ 𝔸²` — survives **all four** kill mechanisms, with a uniform reason:
the generic plane mixes coordinates so every special locus becomes *punctured* (ℂ\*)
rather than 𝔸¹:

1. **No units kill**: `K_t = A_t+B_t+C_t` is irreducible (degree 7) — no factorization,
   no invertible cofactor.
2. **No u-trap**: the u=0 fiber is the graph `z = (5x³−x²+2x+16)/x⁵` over `x ∈ ℂ*` — a ℂ*.
3. **No level-2 u-trap**: `{1+AB=0} ∩ Σ₄ = F⁻¹(Γ)` with `Γ = {(s,−1/s,(2+5s²−s)/s⁴)} ≅ ℂ*`
   (verified `K_t ≡ 1` on Γ); punctured base ⇒ no 𝔸¹-components.
4. **No A-trap**: the `{A=0}`-fiber splits along `A = u·R₀` — reducible.

**Decisive open test: `e(Σ₄)`** via the two-level deficiency stratification over P.
First input computed: the first-level deficiency curve `D₁ = {Λ*=0}∩P` is an
irreducible quartic in (a,b) with **`e(D₁) = 4·(1−6) + 19 = −1`** (six branch values of
the 4:1 b-projection, 19 fiber points over them, constant leading coefficient). The
second-level curve `E₄` (elimination pipeline as in §9) and the stratified assembly
remain: `e(Σ₄) ≠ 1` kills; `e(Σ₄) = 1` escalates to `Cl`/Makar-Limanov/κ̄.

## Reproducing

```
python3 verify_3d_counterexample.py   # the announced map: Keller + 3 preimages
python3 reduction_principle.py        # det J_F = det J_G / γ², compressed map
python3 family_3d.py                  # derived family + NEW (8,7,5) instance
python3 rigidity_2d.py                # Theorem A + two-piece sector rigidity
python3 belyi_k3.py                   # k=3 isotope deg-13 Belyi (live candidate engine)
python3 belyi_deg16.py                # deg-16 dessin existence (combinatorial)
python3 belyi16_exact.py              # EXACT deg-16 Belyi + (99,66) near-miss over Q(sqrt(-3))
python3 multisection_2d.py            # multisection reformulation, collision leaf, linearization
python3 iterated_preimage.py          # Sigma = {B∘F=0}: irreducible, 9:1 etale; the dichotomy
python3 ams_obstruction.py            # resolution: Sigma (and S1, {B=c}) are NOT A^2
python3 candidate_sigma_prime.py      # second-generation candidate Sigma' = {A o F = 1}
python3 traphunt_sigma_prime.py       # round 1 fiber computations (conclusion superseded by 9.3)
python3 level_set_classification.py   # units kill + u-trap: no coordinate level surface is A^2
python3 generation4.py                # generation 4 survives all four mechanisms; e(D1) = -1
```

## Sources

- [The new counterexample to the Jacobian conjecture — Secret Blogging Seminar, 2026-07-20](https://sbseminar.wordpress.com/2026/07/20/the-new-counterexample-to-the-jacobian-conjecture/)
- [The Jacobian counterexample, explained — jacobianfun.org](https://jacobianfun.org/jacobian-explained)
- [Direct Consequences of the Three-Dimensional Counterexample to the Jacobian Conjecture — Zihan Zhang](https://zzhang-iu.github.io/papers/direct-consequences-jacobian/index.html)
- [Fable 5 Jacobian Conjecture Claim — explainx.ai](https://explainx.ai/blog/fable-5-jacobian-conjecture-counterexample-alpoge-july-2026)
- [Jacobian Conjecture — Wolfram MathWorld](https://mathworld.wolfram.com/JacobianConjecture.html)
- [Domrina–Orevkov, four-sheeted polynomial mappings of ℂ² (via Springer)](https://link.springer.com/article/10.1007/s13366-014-0208-4)
- [van den Essen, The Jacobian Conjecture: survey (Banach Center Publ.)](https://matwbn.icm.edu.pl/ksiazki/bcp/bcp31/bcp31116.pdf)
