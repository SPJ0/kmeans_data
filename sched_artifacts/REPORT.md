# Single-machine weighted completion time: does a schedule with cost <= 600 exist?

**Answer: Yes.** A feasible schedule with total weighted completion cost **593** exists
(593 <= 600). It is in fact the global optimum.

## The schedule

Processing order: **A → C → H → E → D → F → G → B**

| Job | r | p | w | Start S | Completion C | w·C |
|-----|---|---|---|---------|--------------|-----|
| A | 0  | 7  | 1 | 0  | 7  | 7   |
| C | 8  | 2  | 8 | 8  | 10 | 80  |
| H | 8  | 2  | 4 | 10 | 12 | 48  |
| E | 10 | 4  | 5 | 12 | 16 | 80  |
| D | 16 | 2  | 8 | 16 | 18 | 144 |
| F | 7  | 3  | 2 | 18 | 21 | 42  |
| G | 11 | 5  | 3 | 21 | 26 | 78  |
| B | 0  | 12 | 3 | 26 | 38 | 114 |
| **Total** | | | | | | **593** |

(Listed in processing order; the machine idles on [7, 8) waiting for C's release.)

Feasibility by inspection: every start is at or after its release time (A 0≥0, C 8≥8,
H 10≥8, E 12≥10, D 16≥16, F 18≥7, G 21≥11, B 26≥0), each completion is start+duration,
and the intervals [0,7), [8,10), [10,12), [12,16), [16,18), [18,21), [21,26), [26,38)
are pairwise disjoint.

## How it was found

`solve.py` enumerates all 8! = 40,320 job permutations. For a fixed processing order the
cost-minimizing timing is the earliest-start (left-shifted) schedule
`S_j = max(previous completion, r_j)`; pushing any job later only increases its own
completion time and can never decrease a later job's, so left-shifting is optimal for
that order. Every feasible schedule induces some permutation, hence this enumeration is
exact. Minimum over all orders: **593**, attained by A,C,H,E,D,F,G,B. Since 593 <= 600
the answer is yes; the exhaustive search additionally shows 593 is the global optimum
(so 600 has slack of 7).

## Verification

`verify.py` is written independently of the construction: it re-transcribes the job data
from the problem statement, reads `schedule.json`, and checks the five required
properties. It does not import or call `solve.py`. Actual output:

```
PASS  exactly the eight jobs, each once
PASS  A: start 0 >= release 0
PASS  A: completion 7 == start + duration 7
PASS  B: start 26 >= release 0
PASS  B: completion 38 == start + duration 12
PASS  C: start 8 >= release 8
PASS  C: completion 10 == start + duration 2
PASS  D: start 16 >= release 16
PASS  D: completion 18 == start + duration 2
PASS  E: start 12 >= release 10
PASS  E: completion 16 == start + duration 4
PASS  F: start 18 >= release 7
PASS  F: completion 21 == start + duration 3
PASS  G: start 21 >= release 11
PASS  G: completion 26 == start + duration 5
PASS  H: start 10 >= release 8
PASS  H: completion 12 == start + duration 2
PASS  no overlapping intervals
PASS  total weighted completion cost 593 <= 600

job     start  completion  weight        w*C
A           0           7       1          7
B          26          38       3        114
C           8          10       8         80
D          16          18       8        144
E          12          16       5         80
F          18          21       2         42
G          21          26       3         78
H          10          12       4         48
TOTAL                                     593

VERDICT: ALL CHECKS PASSED
```

Exit status 0.

## Artifacts

All under `/home/user/kmeans_data/sched_artifacts/`:

- `jobs.json` — the eight jobs' release times, durations, weights
- `solve.py` — exhaustive construction; writes `schedule.json`
- `schedule.json` — the machine-readable schedule (order + start/completion per job)
- `verify.py` — independent verifier (`python3 verify.py`, exits 0 on success)
- `REPORT.md` — this report

Reproduce with: `python3 solve.py && python3 verify.py`

## Resource use (measured)

- `solve.py`: 0.15 s wall, ~10 MB peak RSS (40,320 permutations evaluated)
- `verify.py`: 0.03 s wall, ~10 MB peak RSS
- Total session wall time well under the 15-minute allowance (a few minutes, dominated
  by writing this report rather than computation). No network access used.
