"""The degree-16 Belyi map shared by all of Borisov's isotope frameworks.

Profile: over 0: [2^8], over infinity: [3^5, 1], over 1: [13, 1, 1, 1].
Riemann-Hurwitz: 8 + 10 + 12 = 30 = 2*16 - 2  (genus 0, rigid).

Existence (this file, part 1): enumerate all 2,027,025 perfect matchings
sigma0 (type 2^8) of 16 points against a fixed 13-cycle sigma1 (type 13.1^3)
and count transitive triples with sigma0*sigma1 of type 3^5.1.
Result: 156 labeled solutions -> the dessin exists.

Algebraic model (part 2): put the simple preimage of infinity at u = infinity,
the 13-fold preimage of 1 at u = 0, normalize r(0) = 1.  Then
    phi = c p(u)^2 / r(u)^3,   p monic deg 8, r monic deg 5,
and the whole ramification condition reduces to
    c p^2 = r^3  (mod u^13),
i.e. the power-series square root s = sqrt(r^3) must have s9 = s10 = s11 = s12 = 0
-- four polynomial conditions on (r1, r2, r3, r4).  Equivalently the bilinear
form: 2 p' r - 3 p r' = u^12.  Solutions are found numerically by Newton
iteration on the series conditions (see repository REPORT.md for status).

Run: python3 belyi_deg16.py   (matching enumeration takes ~2-4 minutes)
"""
import itertools

n = 16
sigma1 = list(range(n))
for i in range(13):
    sigma1[i] = (i + 1) % 13

def cycle_type(perm):
    seen = [False]*n; ct = []
    for i in range(n):
        if not seen[i]:
            l, j = 0, i
            while not seen[j]:
                seen[j] = True; j = perm[j]; l += 1
            ct.append(l)
    return sorted(ct, reverse=True)

def matchings(points):
    if not points:
        yield []
        return
    a = points[0]
    for i in range(1, len(points)):
        rest = points[1:i] + points[i+1:]
        for m in matchings(rest):
            yield [(a, points[i])] + m

count, example = 0, None
for m in matchings(list(range(n))):
    sigma0 = list(range(n))
    for a, b in m:
        sigma0[a], sigma0[b] = b, a
    prod = [sigma0[sigma1[i]] for i in range(n)]
    if cycle_type(prod) == [3, 3, 3, 3, 3, 1]:
        seen = {0}; stack = [0]
        while stack:
            x = stack.pop()
            for y in (sigma0[x], sigma1[x]):
                if y not in seen:
                    seen.add(y); stack.append(y)
        if len(seen) == n:
            count += 1
            example = example or m
print("labeled transitive dessins:", count)
print("example matching:", example)
assert count > 0
