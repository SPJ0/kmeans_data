# The Affine Nine Program

A group-theoretic attack on the open **Nine Conjecture**: every simple
planar (sphere) triangulation has a *diagonal coloring* — face vertices
distinct, and opposite vertices of adjacent faces distinct — with 9
colors.  (9 is necessary; 10 is known sufficient; 9 sufficient is open.)

Full development with proofs: [`notes/affine-nine-program.md`](notes/affine-nine-program.md).
Code: `src/`.  Experiments (each reproducible): `experiments/`.

## Proved results

| # | Statement | Where |
|---|-----------|-------|
| 1 | Colors = AG(2,3); a determinant condition per face (with controlled fold faces) forces the entire diagonal property | notes §2, `affine_rep.py` |
| 2 | Global sum of face signs vanishes (sphere cannot wrap the 9-point torus): folds are forced when F ≢ 0 mod 3 | notes §4 |
| 3 | Nine Conjecture reduces to minimum-degree-5 triangulations (degrees 3, 4 classically reducible) | notes §6.5, exp7 |
| 4 | Slope decomposition: representation = PG(1,3) slope field + F₂ lift; lift exists iff vertex parities vanish (Parity Lemma via the medial graph) | notes §8, exp9–10 |
| — | Even-defect theorem: parity defects always come in pairs | notes §8.4, exp11 |
| 5 | Every bipyramid admits a representation (transfer digraph, loops 4 & 5, Frobenius composition) | notes §8.6, exp13 |
| 6 | Every capped antiprism admits one — infinite family **inside** the min-degree-5 class, containing the icosahedron | notes §8.6, exp14, exp14b |
| 7 | Exact Gauss-sum formula for pure-representation counts; Gram matrices factor as C_t ⊗ J | notes §8.7, exp15 |
| 8 | All Gauss sums positive (symplectic normal form): counting = rank-mass combinatorics; the global obstruction falls out of a shift symmetry | notes §8.7 |
| 9 | Exact double-lattice-sum formula for the full representation count; **Nine Conjecture ⟺ positivity of this sum** | notes §8.7, exp16 |

## Verification record

- **Exhaustive**: all 58,715 sphere triangulations with n ≤ 13 admit
  representations (enumeration counts match known values at every n).
- Every extremal instance found with diagonal chromatic number 9
  (including one whose conflict graph is K₉) admits one.
- Min-degree-5 family: geodesic spheres to n = 162, flip variants,
  hill-climbed instances — all pass.
- Dead ends killed by finite proof, not by wandering: naive contraction
  induction (rigid degree-3 sites), universal local extension lemmas
  (fail at every degree), single-edge local search (insufficient moves).

## Status

The Nine Conjecture itself remains open.  The open core, after this
program: *why does the domain-wall lattice sum of Theorem 9 stay
positive on spheres?* — a question now living in Weil-representation /
Gauss-sum territory rather than graph coloring.
