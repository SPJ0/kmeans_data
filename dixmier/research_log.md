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
