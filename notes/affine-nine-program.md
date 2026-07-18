# The Affine Nine Program

An attack on the diagonal coloring problem for planar triangulations via
group-valued colorings.  Everything below is developed from first
principles; proofs are included where claimed.

## 1. The problem

Let `T` be a simple triangulation of the sphere (equivalently, a maximal
planar graph with its unique embedding).  A **diagonal coloring** of `T`
is a vertex coloring such that

* (F) the three vertices of every face receive distinct colors, and
* (D) for every edge `{u,v}`, the two *opposite* vertices `w, x` of the
  two faces `uvw`, `uvx` sharing that edge receive distinct colors.

Nine colors are necessary (there are triangulations — we found one on 9
vertices whose diagonal conflict graph is `K_9` — that need 9), ten are
known to suffice, and the open question is whether **nine always
suffice**.

## 2. The reformulation: colors as points of AG(2,3)

Give the 9 colors the structure of the affine plane `AG(2,3) = F_3^2`.
For `p, q` in `F_3^2` write `det(p,q) = p_x q_y - p_y q_x ∈ F_3`.

**Definition.** Let `phi : V(T) -> F_3^2`.  For a ccw-oriented face
`(u,v,w)` define its **sign**

    s(f) = det( phi(v)-phi(u), phi(w)-phi(u) ) ∈ F_3 .

(The sign is invariant under cyclic rotation of the face, so it is
well-defined for oriented faces.)  Call `phi` an **affine
representation** of `T` if:

* (A1) every face has pairwise-distinct `phi`-values;
* (A2) no two faces sharing an edge have signs summing to `0 (mod 3)`.
  Explicitly, the forbidden adjacent sign pairs are `(1,2)`, `(2,1)`,
  and `(0,0)`.

Note (A1) is automatic when `s(f) ≠ 0`.

**Theorem 1.** *Every affine representation is a diagonal 9-coloring.*

*Proof.*  (F) is (A1).  For (D), let `{u,v}` be an edge with faces
`(u,v,w)` and `(v,u,x)` in ccw orientation, and write `a = phi(u)`,
`b = phi(v)`, `c = phi(w)`, `e = phi(x)`, `s1 = det(b-a, c-a)`,
`s2 = det(a-b, e-b)`.  Suppose `c = e`.  Then
`s2 = -det(b-a, c-b)`, while
`det(b-a, c-a) - det(b-a, c-b) = det(b-a, b-a) = 0`,
so `det(b-a, c-b) = s1`, giving `s2 = -s1`, i.e. `s1 + s2 = 0`,
contradicting (A2).  ∎

So the entire diagonal condition — normally a case-by-case combinatorial
constraint — collapses into one determinant identity.  This is the
central leverage of the program: **prove that every sphere triangulation
admits an affine representation and the Nine Conjecture follows.**

## 3. Local classification of face shapes

Pass to differences: for a directed edge `e = (u,v)` set
`z(e) = phi(v) - phi(u)`.  Around a face, `z(e1)+z(e2)+z(e3) = 0`, and
`s(f) = det(z(e1), z(e2))` for consecutive boundary edges.  The
symplectic form `det` is preserved by `SL(2,3) = Sp(2,3)`.  The allowed
face shapes, as triples `(z1,z2,z3)` with zero sum:

* `s = 1`: `(z1, z2)` is a determinant-1 basis of `F_3^2`.  These form a
  simply-transitive `SL(2,3)`-set: **24 shapes**.
* `s = 2`: determinant-2 bases: **24 shapes**.
* `s = 0` with (A1): forcing `z2 = λ z1` with `z1, z2, z3 ≠ 0` gives
  `λ = 1` in `F_3`, hence `z1 = z2 = z3 = v ≠ 0`: **8 shapes**.  The
  three colors of a degenerate face are `a, a+v, a+2v` — a *complete
  affine line of AG(2,3) traversed as an arithmetic progression*.

So degenerate ("fold") faces are not sloppy exceptions; they are lines
of AG(2,3), and condition (A2) says fold faces form an independent set
in the dual graph, and orientation-classes never meet reversed.

In the pure `s = 0` case, distinctness across the fold edge is
geometric: the fold face's colors lie on a line `L`; a neighboring
non-degenerate face's opposite vertex lies off `L`.

## 4. The global obstruction, and why folds are forced

**Proposition 2.** *For every `phi : V -> F_3^2`,
`Σ_faces s(f) = 0` in `F_3`.*

*Proof.*  `det(b-a, c-a) = a∧b + b∧c + c∧a` where `p∧q = det(p,q)`.
Summing over all ccw faces, every directed edge `(u,v)` occurs in
exactly one face and contributes `phi(u)∧phi(v)`; the reverse edge
contributes the negative.  Everything cancels.  ∎

A sphere triangulation has `F = 2n - 4` faces.  If all faces had sign
`1`, Proposition 2 would force `2n - 4 ≡ 0 (mod 3)`, i.e. `n ≡ 2
(mod 3)`.  Moreover mixed signs `{1,2}` without folds are impossible:
`(1,2)` may not be adjacent, and the dual graph is connected, so a
fold-free representation is sign-constant.  **Hence for `n ≢ 2 (mod 3)`
fold faces are unavoidable.**  This is pleasingly topological: `phi` is
a map from the sphere to the 9-point torus `(Z/3)^2`; the total signed
area of the image must vanish (a sphere cannot wrap a torus,
`π_2(T^2) = 0`), so the map must fold, and our fold faces are exactly
the mod-3 shadow of those folds.

Empirically the pure (fold-free) case fails for some triangulations
*even when* `n ≡ 2 (mod 3)` — there are genuine secondary obstructions,
identified below as monodromy.  The relaxed version (folds allowed) has
so far never failed.

## 5. SL(2,3) monodromy: F_3-frieze structure

Fix a vertex `v` with ccw link `u_1, ..., u_d` and set
`y_i = phi(u_i) - phi(v)`.  Suppose all faces at `v` have sign 1:
`det(y_i, y_{i+1}) = 1`.  Then `(y_{i-1}, y_i)` is always a basis and

    y_{i+1} = -y_{i-1} + t_i y_i ,   with  t_i = det(y_{i-1}, y_{i+1}) ∈ F_3

attached to the *hinge edge* `(v, u_i)`.  In the moving frame
`(y_{i-1}, y_i) -> (y_i, y_{i+1})` the transfer matrix is

    M_t = [[0, -1], [1, t]]  ∈  SL(2,3),

and closing up around the link imposes the **monodromy condition**

    M_{t_d} · ... · M_{t_2} · M_{t_1} = Id   in SL(2,3).

These are precisely quiddity-cycle relations, i.e. a pure affine
representation is a **frieze pattern over F_3** living on the whole
triangulation at once, with structure group `SL(2,3)` — the binary
tetrahedral group, order 24.  Two bonuses:

* The diagonal pair across hinge `(v, u_i)` is `{u_{i-1}, u_{i+1}}`, and
  `phi(u_{i+1}) - phi(u_{i-1}) = y_{i-1} + t_i y_i` (char 3!), which is
  a nonzero coordinate vector in a basis — a second, frieze-native proof
  of diagonal distinctness in the pure case.
* **Vertex conservation law:** for any `phi` (signs arbitrary),
  `Σ_{faces at v} s(f) = det`-area of the closed polygon
  `phi(u_1) ... phi(u_d)` in `F_3` (translation-invariant polygon area).
  Local sign totals are controlled by the geometry of the link image.

## 6. Rigidity at low-degree vertices

For a degree-3 vertex `w` with link triangle `(a,b,c)` (ccw) and
`σ = det(phi(b)-phi(a), phi(c)-phi(a))`, the three face signs at `w`
have sum `σ` (by the vertex conservation law and the identity
`det(y1,y2)+det(y2,y3)+det(y3,y1) = det(y2-y1, y3-y1)`), and must be
pairwise non-opposite.  Enumeration over `{0,1,2}` gives the *only*
allowed multisets:

    σ = 0 : {1,1,1} or {2,2,2}
    σ = 1 : {2,2,0}
    σ = 2 : {1,1,0}

So stacking a vertex into a positively-oriented triangle *forces* a
fold and two negative faces there.  This rigidity is real but, so far,
never fatal.

## 6.5 Reduction: the Nine Conjecture lives on minimum degree 5

The classical greedy argument disposes of low-degree vertices for the
*plain* diagonal coloring problem — exactly where the affine structure
is rigid.  The two tools are complementary.

**Theorem 3 (Reduction).**  *If every sphere triangulation with minimum
degree 5 has a diagonal 9-coloring, then every sphere triangulation
does.*

*Proof sketch (all steps verified mechanically in exp7).*  Induct on
`n`; for `n ≤ 9` give all vertices distinct colors.  Let `v` have
degree 3, link `abc`: delete `v`; `T' = T - v` is a triangulation whose
diagonal colorings satisfy every `T`-constraint not involving `v`
(the new face `abc` and its diagonal pairs only add constraints).  The
conflicts of `v` in `T` are its 3 neighbors plus the 3 opposite
vertices across the link edges: at most 6 < 9 forbidden colors, so any
coloring of `T'` extends.  Let `v` have degree 4, link cycle `abcd`:
at least one of the diagonals `{a,c}, {b,d}` is a non-edge of `T`
(otherwise `{v,a,b,c,d}` spans a `K_5`); delete `v` and retriangulate
with that diagonal, say `ac`.  Every `T`-constraint among surviving
vertices holds in `T'`: consecutive link vertices stay adjacent, the
`T`-diagonal pairs `{a,c}` and `{b,d}` become an edge resp. the
diagonal pair across `ac`.  The conflicts of `v` are its 4 neighbors
plus 4 opposite vertices: at most 8 < 9, so any coloring of `T'`
extends.  Minimum degree ≥ 6 is impossible on the sphere.  ∎

So Conjecture A is *only needed for minimum-degree-5 triangulations* —
the class where every vertex has 10 diagonal conflicts and greedy
arguments die.  This is where the group-theoretic structure must carry
the weight, and empirically it does (see below).

## 7. Experimental record (code in src/, experiments/)

* **Exhaustive**: all simple sphere triangulations with `n ≤ 12`
  (1 + 1 + 2 + 5 + 14 + 50 + 233 + 1249 + 7595 isomorphism classes,
  counts matching the known enumeration, so coverage is complete)
  admit affine representations.  Max diagonal chromatic number over
  `n ≤ 11` (exact): 9, attained from `n = 9` on — consistent with the
  Nine Conjecture and with 9 being necessary.
* **Every random/structured instance tested admits an affine
  representation**, including all 22 instances found with diagonal
  chromatic number ≥ 8, in particular two extremal instances with
  diagonal chromatic number exactly 9 (one on 9 vertices — diagonal
  conflict graph `K_9`; the representation is then a *bijection*
  `V -> AG(2,3)`).
* **Minimum-degree-5 class** (the only class that matters, by Theorem
  3): icosahedron, geodesic subdivisions (`n = 42`, `n = 162`),
  flip-perturbations of these preserving min degree 5, and hill-climbed
  random min-deg-5 triangulations at every feasible `n ≤ 28`: all admit
  affine representations, found by the solver with negligible
  backtracking.
* The pure (fold-free) variant fails on roughly half of the eligible
  (`F ≡ 0 mod 3`) random instances: secondary (monodromy) obstructions
  exist, so the fold-relaxed formulation is the right one.
* **Fold number**: writing `k` for the number of fold faces and taking
  all non-fold faces of sign 1, Proposition 2 forces `k ≡ F (mod 3)`;
  the icosahedron attains this bound (`F = 20`, `k = 2`).  The minimal
  fold number is a new invariant — the minimal mod-3 folding of the
  sphere over the 9-point torus.
* **Extension-lemma data** (exp5/exp6): re-inserting a contracted
  vertex succeeds from *some* representation of the contracted map in
  98% of cases per site, and for 100% of tested triangulations at some
  low-degree site (with a star-repair fallback); but per-site
  counterexamples exist, always at degree-3 sites with very few (9–25)
  representations.  Naive induction is therefore false, and the
  failures sit precisely at configurations that Theorem 3 removes.

## 8. The slope decomposition: from 9 colors to 4 slopes and parity

The face-shape classification of Section 3 says an affine
representation is *equivalent to* a nowhere-zero tension
`z : E -> F_3^2 \ {0}` (closed on faces; on the sphere every such
cocycle is `d(phi)`) subject only to the sign-adjacency rule (A2) —
conditions (A1) plus the shape classification amount to nothing more
than `z(e) ≠ 0` everywhere.

Each nonzero `z(e)` factors as `lambda(e) · w(sigma(e))` with
`sigma(e) ∈ PG(1,3)` its **slope** (4 values; the group
`PGL(2,3) ≅ S_4` acts on them), `w` a fixed representative per slope,
and `lambda(e) ∈ {±1}`.  Facts, each verified mechanically over 1000
representations and by exhaustive enumeration of slope fields on small
triangulations (exp9, exp10):

* **Faces are rainbow or mono.**  A face's three slopes are either
  pairwise distinct (sign ≠ 0) or all equal (fold face).
* **Signs are slope-determined.**  For a rainbow face the sign is a
  function of the slope triple in its ccw cyclic order alone — the two
  admissible `lambda`-patterns per face differ by a global flip, which
  leaves the sign invariant.  Hence rule (A2) is a condition on the
  slope field only.
* **Lifting is F_2-linear.**  Fixing a reference orientation per edge,
  the closedness of `z` on each face pins the pairwise XORs of the
  `mu`-bits (`lambda = (-1)^mu`) of its three edges, with a correction
  bit per (face, edge) for traversal direction.  Care: `lambda` is
  orientation-odd while the slope is orientation-even.
* **Lifting ⟺ vertex parity (Parity Lemma — proved).**  The
  constraints pin `mu(e) XOR mu(e') = r(f, v)` for each *corner*: a
  pair of edges `e, e'` consecutive in the boundary of a face `f`,
  meeting at a vertex `v`.  So the system is a difference system on
  the **medial graph** `M(T)` (vertices: edges of `T`; edges: corners).
  A difference system on a connected graph is solvable iff the
  prescribed differences sum to `0` around every cycle, and the cycle
  space of the sphere-embedded `M(T)` is generated by its face cycles.
  The faces of `M(T)` are of two kinds: faces of `T`, around which the
  sum vanishes identically (the three corner values of a face are the
  pairwise XORs of one base solution, and
  `(b1^b2)^(b2^b3)^(b3^b1) = 0`), and vertices of `T`, around which
  the sum is precisely the vertex parity.  Hence the F_2 lift exists
  iff all vertex parities vanish.  ∎  (Confirmed exhaustively on 480
  enumerated slope fields: agreement 480/480.)

**Consequence (Theorem 4, Slope Decomposition).**  Conjecture A — hence the
Nine Conjecture — is equivalent to a purely combinatorial statement
with no 9-element alphabet left in it:

> Every sphere triangulation carries a map `E -> PG(1,3)` whose faces
> are rainbow or mono, whose mono faces are independent in the dual,
> whose slope-determined face signs never sum to zero across an edge,
> and whose lifting parities vanish at every vertex.

The 9 colors have disappeared into 4 slopes plus one bit — the
structure group has been reduced from `AGL(2,3)` (order 432) through
`SL(2,3)` (order 24) down to `PGL(2,3) ≅ S_4` acting on `PG(1,3)`,
with an abelian `F_2`-cohomological remainder.  This is now a
Tait-coloring-like problem: a bounded local alphabet, local
constraints, and a parity/flow flavor — but over the *projective line
over F_3* instead of three edge colors.

## 8.4 The defect calculus

Two more facts sharpen the slope picture (exp11, exp12):

* **Corner identity / even total defect.**  The three corner bits of
  any face XOR to zero, so summing vertex parities over all vertices
  counts each face's corners once and gives zero: *the number of
  parity-defective vertices of any locally-valid slope field is even.*
  Defects are charges that come in pairs.
* **Gauge dependence.**  Individual corner bits depend on the chosen
  section `w : PG(1,3) -> F_3^2 \ 0` (a gauge); only the vertex
  parities' vanishing is invariant.  In the standard gauge, corner
  bits vanish on faces with three finite slopes and are governed on
  `inf`-faces by the harmonic structure of `PG(1,3)` (any four
  distinct points of the projective line over `F_3` form a harmonic
  range).
* **Tait start and defect annihilation.**  A Tait coloring (which
  exists by 4CT) is a slope field with all faces rainbow on 3 slopes;
  its defects are sign mismatches on dual edges plus vertex parities.
  Greedy single-edge re-sloping annihilates all defects on some
  instances (octahedron, bipyramids) but gets stuck on others
  (icosahedron) even though valid fields exist there — single-edge
  moves are provably too weak a move set, and the natural remedy is
  Kempe-style chain moves: swapping two slopes along an alternating
  cycle, i.e. the `S_4` action applied along cycles of the field.
  Formalizing a defect-transport move ("re-slope along a path to move
  a parity charge, then annihilate charge pairs") is the concrete next
  step of this program.

## 8.5 Connection to Tait colorings

If one insists on using only 3 of the 4 slopes with all faces rainbow,
the slope field is exactly a proper 3-edge-coloring of the dual cubic
graph (a Tait coloring, which exists by the Four Color Theorem), and
the sign condition says all faces read the three slopes in the same
rotational sense — a *uniformly oriented* Tait coloring, which forces
`F ≡ 0 (mod 3)` and generally does not exist.  The fourth slope and
the mono faces are precisely the new freedom this program contributes
over the classical Tait picture.  The question is whether that freedom
is always enough to fix orientation and parity — experimentally, it
always has been.

## 8.6 Proven infinite families (transfer-matrix method)

Because all constraints of a "cylindrical" triangulation are windowed
over a bounded band, valid representations correspond to closed walks
in a finite transfer digraph, and closed walks of two coprime lengths
through a common node give all sufficiently large sizes by Frobenius
composition.  Small sizes are verified directly; every composed
representation is checked independently.  This yields machine-assisted
but finitely-verified theorems:

**Theorem 5.**  *Every bipyramid (double wheel) admits an affine
representation, hence a diagonal 9-coloring.*  (Transfer digraph on
color pairs with apexes normalized to (0,0), (1,1) — legitimate by
2-transitivity of `AGL(2,3)`; loops of lengths 4 and 5 at a common
node; all `m ≥ 12` by composition, `m ≤ 11` direct.  exp13.)

**Theorem 6.**  *Every capped antiprism (gyroelongated bipyramid;
`m = 5` is the icosahedron) admits an affine representation.*  All its
ring vertices have degree 5, so this is an infinite family inside the
critical minimum-degree-5 class.  (Transfer digraph on rung 4-tuples:
306 nodes; closed walks of lengths 3 and 5 at a common node, Frobenius
number 7; all `m ≥ 8` by composition, `m = 3..7` direct.  exp14,
exp14b.)

The same method mechanically extends to any bounded-bandwidth family
(stacked prisms/drums of bounded ring size, etc.); the general
minimum-degree-5 case needs an argument that handles unbounded layer
sizes.

## 8.7 The Gauss-sum formula (Weil-representation avenue)

Let `N_1(T)` be the number of *pure* representations (`s(f) = 1` for
every face).  Expanding the indicator over additive characters of
`F_3`:

    N_1(T) = 3^{-F} Σ_{t ∈ F_3^F}  ω^{-Σ_f t_f} · G(Q_t) ,
    Q_t(φ) = Σ_f t_f · s_f(φ) ,     ω = e^{2πi/3} ,

and the key structural facts (verified exactly on test cases, exp15):

* `Q_t` is a quadratic form on `F_3^{2n}` with Gram matrix
  `C_t ⊗ J`, where `J` is the symplectic form on `F_3^2` and `C_t` is
  the **antisymmetric edge matrix** `C_t[u,v] = t(f_left) - t(f_right)`
  — the coboundary of the face-weighting `t` across each edge.
* `|G(Q_t)| = 3^{2n - rank C_t}` for every `t` (checked for all
  `3^F` weightings on the test triangulations), so

      N_1(T) = 3^{2n-F} Σ_t  ω^{-Σ t} · ε_t · 3^{-rank C_t}

  with `ε_t` a Witt sign.  Since `2n - F = 4` on the sphere:
  `N_1 = 81 · Σ_t ω^{-Σt} ε_t 3^{-rank C_t}`.
* `rank C_t` is a purely combinatorial quantity: `C_t` vanishes on
  edges interior to level sets of `t` on the dual graph, so the sum is
  a **Potts-like domain-wall model**: `t` = an `F_3`-spin
  configuration on faces, weighted by `3^{-rank(boundary operator)}`
  with cube-root-of-unity phases.  Constant `t` gives the leading term.

Verified: tetrahedron (`N_1 = 0`, and the character sum vanishes
exactly — the phases conspire against the positive leading term, as
they must since `F ≢ 0 mod 3` forbids pure representations) and
bipyramid(3) (`N_1 = 648` both ways, exact).

The same expansion applies to the fold-allowing count (the indicator
of `{1, 2, fold}` produces a few character terms per face instead of
one), giving an exact formula for the number of affine representations
as a finite lattice sum of Gauss sums.  **The Nine Conjecture is
thereby equivalent to the positivity of an explicit
Potts-with-phases partition function** — a statement in the territory
of Weil representations and theta-like sums rather than graph
coloring.  The group theory has moved from `SL(2,3)` monodromy to the
metaplectic/Weil side: the Gauss sums `G(Q_t)` are matrix coefficients
of the Weil representation of `Sp` over `F_3`, and the Witt signs
`ε_t` are its quadratic characters.  Determining the sign pattern
`ε_t` combinatorially (e.g. via the domain topology of `t`) is the
concrete open task on this route.

## 9. Conjecture and proof program

**Conjecture A (Affine Nine).**  Every simple triangulation of the
sphere admits an affine representation.  (By Theorem 1 this implies the
diagonal Nine Conjecture; by Theorem 3 it suffices to prove it for
minimum degree 5.)

Status of the attack routes:

1. **Contraction induction with a local extension lemma** — *tested,
   fails in raw form*: extension after contraction is not always
   possible (2% of sites), with all observed failures at degree-3
   sites, where Section 6 shows the sign multiset is *forced*.  Within
   the min-degree-5 world these configurations do not arise, but
   contraction leaves the class; a closed induction needs an operation
   set that stays inside min-degree-5 (vertex splittings generating the
   class from the icosahedron) together with the extension analysis at
   degree-5 sites, where local sign freedom is large.
2. **Flexibility strengthening.**  Prove representations exist in
   quantifiable abundance (transitivity of a local re-coloring groupoid
   on the fiber over each ring), so that some representation of the
   smaller triangulation always extends.  Star-repair experiments
   support this: repair within the closed star fixed most residual
   failures.
3. **Structural construction.**  A Schnyder-type canonical
   construction: integral straight-line embeddings with positively
   oriented faces, reduced mod 3; the conditions become congruence
   conditions on integer face areas, to be engineered via the choice of
   embedding.
4. **Partition-function positivity (wild).**  The number of
   representations is a tensor-network contraction over the dual cubic
   graph with `SL(2,3)`-structured local weights; Proposition 2 already
   shows the naive character-weighted sum collapses to `9^n`.  A
   Penrose-style identity expressing the representation count as a
   manifestly positive quantity would prove Conjecture A without any
   configuration analysis.
5. **Quaternionic avenue (speculative).**  `SL(2,3)` is the binary
   tetrahedral group, the unit group of the Hurwitz quaternions; a pure
   representation is a flat `2T`-structure, suggesting quaternionic
   coordinates for the frieze monodromy problem.
6. **Möbius alternative (recorded for completeness).**  The 9 colors
   can instead be `P^1(F_8)` with its sharply 3-transitive
   `PGL(2,8)`-action; a diagonal 9-coloring is exactly a map to
   `P^1(F_8)` with injective faces whose edge cross-ratios avoid
   `{0, 1, ∞}` (the conflict `phi(w) = phi(x)` is *equivalent* to
   cross-ratio 1).  This is a perfect developing-map/monodromy
   formulation, but a crude entropy count (6 cross-ratio values per
   edge against `|PGL(2,8)| = 504` per vertex relation) suggests it is
   tighter than the affine formulation; kept as a reserve line.
