#!/usr/bin/env python3
P = [int(x) for x in open("P.txt").read().split()]
A = [0, 1, 4, 6]          # perfect ruler: differences {1,2,3,4,5,6}
q = 993
B = sorted(993*a + p for a in A for p in P)
assert len(B) == len(set(B)) == 128
open("solution.txt", "w").write(" ".join(map(str, B)) + "\n")
print("|P| =", len(P), " window =", max(P))
print("|B| =", len(B), " max =", max(B))
