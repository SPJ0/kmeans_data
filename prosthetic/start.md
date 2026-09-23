# Workspace entry: difference basis |B|<=128 covering 1..6166

## How to use this file
- Read at start/resume. Top section = current status; keep it short and current.
- Update when a hypothesis is confirmed/killed or the best number changes.
- Dead ends go in "Killed ideas" with a one-line reason.
- Lesson from this run (keep): before long stochastic searches, enumerate the small *finite*
  structural family exhaustively and compute the one quantity the counting argument says matters.

## Status: SOLVED and verified
- work/solution.txt: 128 distinct nonnegative ints, max 6742, covers every d in 1..6166.
  Verify: `cd work && python3 verify.py solution.txt` -> VERIFIED.
- Construction (work/build_solution.py): Singer perfect difference set mod m=993 (q=31, 32 elems,
  work/singer.py), multiplied by u=629, cut at gap 7 to get integer lift X in [0,993) whose positive
  differences contain ALL of 1..208 (max possible over all 7040 lifts; work/lifts.py).
  B = X + 993*{0,1,4,6}. Leech argument: covers 1..6m + (first gap of P) - 1 = 5958+208 = 6166.

## Path that got here (chronological)
1. leech_sa.c: SA over (u, rotations c_i, offsets t_i): best 6091. Analysis (analyze.py) showed the
   SA had converged to "same lift X, perturbed offsets" and within-copy diffs contributed 0 unique.
2. Counting note: 6166 = 6*993 + 208 exactly -> suggests Leech product with P containing [1,208].
3. lifts.py enumerated all 7040 distinct lifts (220 multipliers x 32 cuts): max first-gap = 208.
   Exactly the needed value -> solution immediately.

## Counting insight (general, reusable)
- Leech product X + m*{0,1,4,6} (X a lift of a perfect difference set mod m, X in [0,m)) covers
  1..6m + L where [1,L] is the longest initial run in positive differences of X.
- Cross pair of copies gives <= m distinct values; region (Dm,(D+1)m) fully covered iff sign-set
  S_{D+1} subset of S_D.

## Killed ideas
- Pure element-level SA from random start (caps ~5000 of 6166).
- Element SA from structured 6091 start: no improvement (landscape too rigid).
- lift_sa.c (+-m moves) from random init: 5805.
- Bose affine set q=32 mod 1023 (bose.py): residues = 0 mod 33 missing; region-counting shows
  ~31 losses per region; not pursued (runs killed once Singer solution found).
