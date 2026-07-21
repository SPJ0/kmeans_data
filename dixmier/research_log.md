# Research log — JC_2 campaign

## 2026-07-21 (box paused; literature + local work)

### Prime-degree exclusion reshapes the multiplicity program

Moskowicz, *There are no Keller maps having prime degree field extensions*
(arXiv:2407.13795): over C there is no planar Keller map with
[C(x,y) : C(p,q)] prime. Unconditional.

Consequences for a hypothetical JC_2 counterexample f = (p,q):

- Generic multiplicity k = [C(x,y):C(p,q)] cannot be 2 or 3 (or any prime).
  Smallest open multiplicity: **k = 4**, then 6, 8, 9.
  (Contrast: the Alpöge JC_3 map is 3-to-1 — legal only because the
  exclusion is 2D-specific.)
- k = 4 cases by Galois closure of the degree-4 extension:
  - **Z/4, V4 (Galois), D4**: there is an intermediate field M with
    [C(x,y):M] = [M:C(p,q)] = 2, i.e. the counterexample factors
    birationally as a tower of two degree-2 maps. Each step is exactly the
    setting of Trushin, *Contracted divisors and degree-two maps*
    (arXiv:2605.26390, May 2026) — use its constraints on contracted /
    dicritical divisors to squeeze both steps. Deck groups here are finite
    (abelian: Z/4, V4) subgroups of the Cremona group — classified (Blanc),
    finitely many conjugacy classes, each with rational invariant field
    (Castelnuovo) => finitely many structured families to sweep.
  - **A4, S4**: no intermediate field; only the cubic-resolvent subfield of
    the closure is available. Hardest case; no tower shortcut.
- Program: enumerate the order-4 Cremona classes, write the invariant-field
  generators for each, and pose "Keller pair inside the invariant field"
  as finite coefficient systems per degree box — same msolve pipeline.

### No-Galois lemma (sharpens the k=4 case split)

A Keller map is everywhere étale (jac const != 0). If the generic-fiber
extension were Galois with every deck map regular on C^2, a deck map would
be a finite-order automorphism of C^2, hence linearizable
(Jung–van der Kulk => finite subgroups of Aut(C^2) conjugate into GL_2),
hence with a fixed point — contradicting freeness on the étale cover.
Classical corollary of the same circle: a PROPER Keller map is a trivial
cover of C^2 (simply connected), i.e. an automorphism. So any counterexample
is non-proper, and its deck maps (when Galois-partial structure exists) are
only partially defined — the Z/4 and V4 closures at k = 4 are ruled out in
the finite/regular regime; the live quartic closures are D4, A4, S4, with
the D4 case still offering a degree-2 tower step for the contracted-divisor
squeeze.

### Local (box-independent) work

- invariants.py D=12 sweep of u∘F^k = a·u + b running on the Mac
  (D<=10 already empty for k=1,2,3).
- To scrutinize when time permits: the Moskowicz proof (it is load-bearing
  for abandoning k=2,3 searches; independent verification prudent).

### The Alpöge mechanism, reverse-engineered (first-principles session)

- Jelonek non-properness set computed exactly (jelonek2.py):
  **S_F : u2^3 u3 + 27 u1^2 u3^2 - 18 u1 u2 u3 - u2^2 + 16 u1 = 0**,
  irreducible quartic, Z/3-semi-invariant, escape only through the
  x-direction at infinity. Honest fibers stay 3 points even on S_F (the
  escaping 2-parameter family is *extra*, concentrated over the quartic).
- Escape asymptotics (verified on the u1=0 branch, which gives the
  u2*u3 = 1 slice): x -> inf with xy -> a and x^2 z -> 2-3a bounded —
  i.e. torus-invariant coordinates bounded, weight-1 coordinate escaping.
- Structural key: every component of F is supported in a SINGLE COSET of
  3Z in the torus-weight lattice (F1 ≡ 1, F2 ≡ -1, F3 ≡ 1 mod 3).
  gcd(coset, d) = 1 explains why no proper-subalgebra certificate applies:
  the map is honestly 3-to-1, not a graded-subalgebra artifact.

### 2D transplant: the coset construction ansatz

Grade C[x,y] by w = deg_x - deg_y. Ansatz: p supported in w ≡ +1 (mod d),
q in w ≡ -1 (mod d), jac(p,q) = 1, plus ONE imposed collision
f(v) = f(v'), v != v' (saturated). Any solution = non-injective Keller map
= JC_2 counterexample outright. Sizing forced by theory: Moh kills
max-degree <= 100; Moskowicz kills prime multiplicity. Target shot:
d = 56, bidegrees (112, 168) = 56·(2,3) — GGV needs gcd >= 16, Moh needs
deg > 100, Moskowicz needs composite k. Coset support cuts the system to a few
hundred coefficients — one msolve job (jc2_construct.py), not a sweep.
Dichotomy: NONEMPTY = explicit counterexample; EMPTY = that ansatz shape
is excluded exactly — either outcome is information.

### Status of certified layers (all EMPTY, certificates in repo)

- DC_1  B=16: 56/60 (missing: the four d=2 giants; msolve pending box).
- JC_2  B=16: 60/60 — layer complete.
- JC_2  B=17: launched (64 cells), interrupted by box pause; resumes free.
- JC_2  dihedral B=17..~26: 861 cells.
- DC_1  dihedral B=17 (partial): 96 cells.

### Resume checklist (when box is back)

    cd kmeans_data/dixmier
    nohup setsid python3 fleet.py 32 16          > fleet_resume.log 2>&1 &   # 4 d=2 giants
    nohup setsid nice -n 10 python3 jc2_fleet.py 8 17  > jc2_fleet_B17.log 2>&1 &
    nohup setsid nice -n 12 python3 jc2_sym_fleet.py 6 17 32 > jc2_sym_fleet.log 2>&1 &
    nohup setsid nice -n 8  python3 dc_sym_fleet.py 5 17 24  > dc_sym_fleet.log 2>&1 &

  (all fleets resume from existing cell_*.out certificates), then re-arm
  the anomaly monitor + heartbeat cron.

### Above-the-Moh-wall exclusions (targeted construction shots, local Mac)

- CONSTRUCT d=56 (112,168) coset ±1, collision dx: **EMPTY** (376 vars,
  696 eqs, minutes). First exclusion beating Moh's degree-100 wall: the
  exact Alpöge coset shape at minimal legal size admits no non-injective
  Keller pair — not even a second common zero of (p,q) (both vanish at 0
  automatically in this ansatz, and a second common zero v gives the
  collision f(v) = f(0) = (0,0) outright).
- Rungs d=10 (20,30), d=24 (48,72): EMPTY (Moh-consistent, plumbing+timing).
- In flight: dy variant; cosets ±3, ±5; d = 51, 52, 55, 57; corner (3,4).
