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
  `(0:[2⁸], ∞:[3⁵,1], 1:[13,1³])`. Writing it as `φ = c·p²/r³` (p monic deg 8, r monic
  deg 5), the entire ramification condition collapses to the single bilinear identity
  **`2p′r − 3pr′ = u¹²`** — 12 equations; p is triangularly determined by r, leaving 4
  conditions on 4 coefficients of r (computation running; Newton + Groebner).
- on the (−2)-curve of the k=3 isotope: degree 13, profile
  `(∞:[13], 0:[3,3,3,1,1,1,1], 1:[7,1⁶])`. **Constructed explicitly**
  (`belyi_k3.py`): writing `g = A³B` with the 7-fold point at 0 forces
  `g′ = 13t⁶A²`, `g(0)=1`, and the single condition `A³ | g` gives 9 equations in the 3
  coefficients of A. The Groebner basis is triangular over a degree-65 polynomial that
  is a **quintic in a₂¹³** (the 13th roots of unity are the residual scaling); the
  quintic is irreducible over ℚ — the dessin's moduli field has degree 5, matching the
  count of admissible plane trees. A real solution was extracted to 40 digits and the
  full profile verified (7-fold root exact, A, B, D squarefree and coprime).

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

## Reproducing

```
python3 verify_3d_counterexample.py   # the announced map: Keller + 3 preimages
python3 reduction_principle.py        # det J_F = det J_G / γ², compressed map
python3 family_3d.py                  # derived family + NEW (8,7,5) instance
python3 rigidity_2d.py                # Theorem A + two-piece sector rigidity
```

## Sources

- [The new counterexample to the Jacobian conjecture — Secret Blogging Seminar, 2026-07-20](https://sbseminar.wordpress.com/2026/07/20/the-new-counterexample-to-the-jacobian-conjecture/)
- [The Jacobian counterexample, explained — jacobianfun.org](https://jacobianfun.org/jacobian-explained)
- [Direct Consequences of the Three-Dimensional Counterexample to the Jacobian Conjecture — Zihan Zhang](https://zzhang-iu.github.io/papers/direct-consequences-jacobian/index.html)
- [Fable 5 Jacobian Conjecture Claim — explainx.ai](https://explainx.ai/blog/fable-5-jacobian-conjecture-counterexample-alpoge-july-2026)
- [Jacobian Conjecture — Wolfram MathWorld](https://mathworld.wolfram.com/JacobianConjecture.html)
- [Domrina–Orevkov, four-sheeted polynomial mappings of ℂ² (via Springer)](https://link.springer.com/article/10.1007/s13366-014-0208-4)
- [van den Essen, The Jacobian Conjecture: survey (Banach Center Publ.)](https://matwbn.icm.edu.pl/ksiazki/bcp/bcp31/bcp31116.pdf)
