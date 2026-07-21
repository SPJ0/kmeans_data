# Dixmier Conjecture (DC1) — computational assault: handoff bundle

## Context

Following the July 2026 disproof of the Jacobian conjecture in dimension 3 (and with it
DC_n for all n >= 3 via an explicit non-surjective endomorphism of A_3), the remaining
open cluster is {DC_1, DC_2, JC_2, PC_2}, with falsity flowing
DC_1 false => JC_2 false. This bundle attacks DC_1 directly.

## Framework (all validated in-session)

- `weyl.py` — exact arithmetic kernel for the Weyl algebra A_1 in the generalized-Weyl
  (GWA) presentation: elements are dicts {weight w: poly in theta}, theta = x*d.
  Cross-validated against an independent normal-ordering implementation.
- Key structural facts proved:
  1. **Sublattice certificate**: if a pair P,Q with [Q,P]=1 has weight support in
     d*Z (d >= 2), then WLOG both live in the proper graded subalgebra
     S_d = ⊕_{w in dZ} C[theta] v_w, so ANY such pair is automatically a
     counterexample to DC_1 — non-generation is free.
  2. **Single-weight collapse**: C*-homogeneous P admits a Dixmier partner iff
     P = c*d/dx (trivial pair). Proof: one difference equation.
  3. Guccione–Guccione–Valqui wall: any counterexample has
     B := gcd(v(P), v(Q)) >= 16 (Bernstein degrees). First open configuration:
     B = 16, corner (2,3), i.e. (v(P), v(Q)) = (32, 48).

## Cell machinery

- `cascade2.py` — builds the full bilinear system [Q,P] = 1 for a cell:
  S_d-supported pairs with Bernstein caps (degP, degQ), with corner-type saturation
  ('extreme' = x^degP / x^degQ led; 'w0' = theta^(degP/2) / theta^(degQ/2) led).
  Verdict via Groebner: basis == [1] <=> cell provably EMPTY.
- `descent4.py` — fast triangular level-descent for the S_16 (32,48) extreme cell on
  sympy sparse rings: eliminates all Q-unknowns linearly (Q enters [Q,P] linearly),
  deposits the obstruction ideal on the ~37 P-variables. Produced
  125 constraints in 37 vars (pickle ~2GB as Exprs; regenerate rather than copy).
- `triage.py` — incremental smallest-first Groebner on the saved constraint ideal
  (inconsistent subset => whole cell closed).
- `verdict.py` — mod-p / exact Groebner on the saved ideal.
- `partners.py` — linear partner-classification for fixed P (controls + probes).

## Results so far

- Excluded cells S_2(4,6), S_3(6,9), S_4(8,12) both corners, S_5(10,15),
  S_8(16,24) both corners: all provably EMPTY, exact over Q — matches published
  theory everywhere they overlap (correctness ladder green).
- S_16(32,48) extreme corner: cascade complete; obstruction ideal
  (125 constraints / 37 vars) computed; final Groebner verdict IN PROGRESS on the
  small box (sympy is the bottleneck).

## What to run on the big machine (priority order)

0. Install real Groebner engines — this is worth more than the cores:
   `apt install singular` and build/install **msolve** (https://msolve.lip6.fr,
   also on conda-forge). Optionally python-flint. Re-express the constraint systems
   in msolve input format; sympy remains the system *builder* only.
1. Re-run S_16 (32,48) extreme cell end-to-end (descent4 regenerates the ideal in
   ~3.5h single-core; the per-level substitutions parallelize per t-coefficient if
   ported to multiprocessing), verdict via msolve over Q and mod several primes.
2. Close the w0 corner of S_16 (32,48): needs the banded parametric linear solve
   (pivot = multiplication by Delta_w p_0, triangular with constant diagonal -16w
   after making p_0 monic) — or brute msolve on the full 118-var bilinear system,
   which msolve may simply eat.
3. Fleet sweep of the entire B = 16 layer: cells for ladder data
   (delta, d) with 2*delta + d = 16, d in {2,4,...,16}, both corner types,
   both (2,3) and (3,2) corners. Each cell is an independent process.
4. If all of B=16 closes: sweep B = 17, 18, ... mechanically. If any cell is
   NONEMPTY: extract the solution point, reconstruct (P,Q), verify [Q,P] = 1 with
   weyl.py — that is a counterexample to DC_1 and hence to the 2D Jacobian
   conjecture (certificate is machine-checkable in seconds).

## Machine notes

- One cell peaked at ~9GB RSS under sympy; msolve will be leaner. For a
  30-cell parallel fleet budget ~4-8GB per worker.
- Everything is exact rational arithmetic; no numerics anywhere.
