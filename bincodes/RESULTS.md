# Binary codes of length 8 with minimum Hamming distance 3

Investigation date: 2026-09-22. Working dir: `/home/user/kmeans_data/bincodes`.
Pre-task snapshot of the earlier (difference-basis) investigation:
`/home/user/kmeans_data/snapshots/diffbasis_pre_bincodes_20260922T170440Z`
(the earlier work is also at git commit `ab4d7ca`).

**Question.** Collections of distinct 8-bit strings, every two of which differ in
at least 3 positions. Does a collection of exactly 20 exist? Of exactly 29?

## Conclusion

| size | verdict |
|---|---|
| **20** | **EXISTS** — explicit collection in `code20.txt`, verified by two separate checkers |
| **29** | **IMPOSSIBLE** — ruled out by the sphere-packing (Hamming) bound; proof below |

## Case 20 — exists

`code20.txt` (found by local search in `construct20.py`, 0.87 s):

```
00001011  00010010  00011101  00100001  00101100
00110111  01000110  01010001  01101111  01110100
01111010  10000101  10011110  10100110  10110000
10111011  11000000  11010111  11100011  11111101
```

Verification (`verify_code.py`, written separately from the construction and
computing distances character by character, not with bit tricks):

```
strings found         : 20 (required exactly 20)
all length 8          : True
all symbols in {0,1}  : True
all distinct          : True
pairs checked         : 190 (expected 190)
minimum distance      : 3 (required >= 3)
distance distribution : {3: 61, 4: 75, 5: 29, 6: 15, 7: 9, 8: 1}
RESULT                : PASS
```

Second, independently written verifier (`verify_code.c`):
`strings=20  length=8  pairs=190  min distance=3  RESULT: PASS`

All 190 pairs were checked explicitly; none was skipped or sampled.

## Case 29 — impossible

**Theorem.** There is no collection of 29 distinct binary strings of length 8
whose pairwise Hamming distances are all at least 3.

**Proof.** Let `C` be a set of length-8 binary strings with `d(x,y) >= 3` for all
distinct `x, y` in `C`, and put `M = |C|`. For `c` in `C` define the ball
`B(c) = { z in {0,1}^8 : d(z,c) <= 1 }`, consisting of `c` itself together with
the 8 strings obtained by flipping exactly one bit, so

    |B(c)| = C(8,0) + C(8,1) = 1 + 8 = 9.

*The balls are pairwise disjoint.* Suppose `z` lies in `B(c1)` and `B(c2)` with
`c1 != c2` in `C`. Hamming distance is a metric, so by the triangle inequality

    d(c1,c2) <= d(c1,z) + d(z,c2) <= 1 + 1 = 2,

contradicting `d(c1,c2) >= 3`. Hence no such `z` exists.

*Counting.* The `M` balls are pairwise disjoint subsets of `{0,1}^8`, which has
`2^8 = 256` elements, so

    9M <= 256,  i.e.  M <= 256/9 = 28.44...,  so  M <= 28.

Since `29 > 28`, no collection of 29 such strings exists. ∎

(The same argument shows every size from 29 to 256 is impossible. It does *not*
decide sizes 21–28; those were not asked about and are **not** settled here.
For the record, the literature value of the maximum, `A(8,3) = 20`, would make
21–28 impossible as well, but that exact value is background knowledge, not
something proved or checked in this investigation. What this investigation
establishes on its own is `20 <= A(8,3) <= 28`.)

## Files

| path | role |
|---|---|
| `code20.txt` | the 20-string collection (the answer for size 20) |
| `construct20.py` | search procedure that produced it |
| `verify_code.py` | independent verifier (Python, character-by-character distances) |
| `verify_code.c` | second independent verifier (C) |
| `RESULTS.md` | this file |

No candidate file exists for size 29, because no such collection exists.

## Reproduce

```sh
python3 construct20.py                      # -> code20.txt
python3 verify_code.py code20.txt 20 8 3
gcc -O2 -o verify_code verify_code.c && ./verify_code code20.txt 20 8 3
```
