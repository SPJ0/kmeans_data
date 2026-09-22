# A 128-element difference basis for 1..6166

**Problem.** Find a set `B` of at most 128 distinct nonnegative integers such that every
integer `d` with `1 <= d <= 6166` equals `|a - b|` for some `a, b` in `B`.
(Ordinary integer differences; elements may exceed 6166.)

**Result.** Solved. `solution.txt` holds 128 distinct nonnegative integers covering every
distance 1..6166. Verified by two independently written checkers (`verify.py`, `verify2.c`).
The first uncovered distance is 6167, so the construction is exactly tight at 6166.

## The construction

Let `q = 31^2 + 31 + 1 = 993`.

1. **`P` — a Singer (planar) difference set mod 993.** Built from `GF(31^3)`: with `x`
   primitive modulo the irreducible cubic `x^3 = 2x^2 + 3`, take
   `P0 = { i mod 993 : the x^2-coefficient of x^i is 0 }`. This has 32 elements and every
   nonzero residue mod 993 occurs **exactly once** as a difference of `P0`.
2. **Choose the multiplier.** `t*P0 mod 993` is again a planar difference set for every unit
   `t`. Scanning all units, `t = 172` maximises the largest cyclic gap: **209**. Rotate so
   that gap wraps around; the resulting `P` (in `P.txt`) lies inside the window `[0, 784]`.
3. **Combine with a perfect ruler.** `A = {0, 1, 4, 6}` has differences exactly `{1,...,6}`.

   **`B = P + 993 * A`**  — 4 blocks of 32 marks = **128 elements**, max element 6742.

## Why it covers 1..6166

Write `D` for the set of ordinary (integer) positive differences of `P`.

* Planarity: for each `e` in `[1,992]`, exactly one of `e`, `993-e` lies in `D`.
* Window: `P` is inside `[0,784]`, so every element of `D` is `<= 784`. Hence for
  `e <= 208` the partner `993-e >= 785` cannot be in `D`, so **`e` itself is in `D`**:
  `[1,208]` is a subset of `D`.
* `A - A` contains `0,1,2,3,4,5,6`.

Take any `v` in `[1,6166]` and write `v = 993c + e` with `1 <= e <= 993`; then `c <= 6`.
  - `e = 993`: `v = 993(c+1)` with `c+1 <= 6` — a pure block-offset difference.
  - `e` in `D`: `v = 993*c + e` with `c` in `A-A` and `e` a difference of `P`.
  - otherwise `993-e` is in `D` and `v = 993(c+1) - (993-e)`, which needs `c+1 <= 6`,
    i.e. `c <= 5`. The only remaining case is `c = 6`, where `e = v - 5958 <= 208`,
    and there `e` is in `D` by the window argument.

So the reachable length is `6*993 + (gap - 1) = 5957 + 209 = 6166`.

## Files

| file | role |
|---|---|
| `solution.txt` | **the answer**: 128 integers |
| `P.txt` | the 32-element rotated Singer difference set |
| `singer.py` | builds `P0` in `GF(31^3)`, checks planarity, scans multipliers for the largest gap |
| `build.py` | `B = P + 993*{0,1,4,6}` -> `solution.txt` |
| `verify.py` | independent verifier (Python): count, nonnegativity, distinctness, coverage |
| `verify2.c` | independent verifier (C), written separately; also reports the longest covered prefix |
| `wichmann.py` | Wichmann ruler baseline (128 marks, length 5502) |
| `blocks.c`, `blocks2.c`, `blocks3.c`, `db.c`, `sa3.c`, `rnr.c`, `pipe.sh` | the search programs used before the algebraic construction was found (best they reached at N=6166 was 274 uncovered) |

## Reproduce

```sh
python3 singer.py     # -> P.txt   (prints: max cyclic gap = 209 -> N = 6166)
python3 build.py      # -> solution.txt
python3 verify.py solution.txt 128 6166
gcc -O2 -o verify2 verify2.c && ./verify2 solution.txt 128 6166
```
