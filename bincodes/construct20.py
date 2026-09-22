#!/usr/bin/env python3
"""Find 20 binary strings of length 8 with pairwise Hamming distance >= 3.
Local search (tabu/SA style) minimising the number of violating pairs."""
import random, sys, time

n, M, dmin = 8, 20, 3
N = 1 << n
POP = [bin(x).count("1") for x in range(N)]
def dist(a, b): return POP[a ^ b]

def cost(S):
    c = 0
    for i in range(len(S)):
        for j in range(i + 1, len(S)):
            if dist(S[i], S[j]) < dmin: c += 1
    return c

def search(seed, iters=400000):
    rng = random.Random(seed)
    S = rng.sample(range(N), M)
    c = cost(S)
    best, bestS = c, S[:]
    T = 2.0
    for it in range(iters):
        if c == 0: return 0, S
        T = 2.0 * (0.02 / 2.0) ** ((it % 50000) / 50000)
        # pick a codeword that participates in a violation
        viol = [i for i in range(M) if any(i != j and dist(S[i], S[j]) < dmin for j in range(M))]
        i = rng.choice(viol) if viol else rng.randrange(M)
        old = S[i]
        newv = rng.randrange(N)
        if newv in S: continue
        before = sum(1 for j in range(M) if j != i and dist(old, S[j]) < dmin)
        after  = sum(1 for j in range(M) if j != i and dist(newv, S[j]) < dmin)
        d = after - before
        if d <= 0 or rng.random() < pow(2.718281828, -d / T):
            S[i] = newv; c += d
            if c < best: best, bestS = c, S[:]
    return best, bestS

t0 = time.time()
for seed in range(1, 200):
    c, S = search(seed)
    if c == 0:
        S = sorted(S)
        with open("code20.txt", "w") as f:
            for w in S: f.write(format(w, "08b") + "\n")
        print("FOUND 20 codewords, violations = 0, seed =", seed,
              ", %.2fs" % (time.time() - t0))
        sys.exit(0)
print("no solution found")
