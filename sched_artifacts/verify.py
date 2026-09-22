import json
# Job data transcribed independently from the problem statement.
DATA = {
 'A': (0, 7, 1), 'B': (0, 12, 3), 'C': (8, 2, 8), 'D': (16, 2, 8),
 'E': (10, 4, 5), 'F': (7, 3, 2), 'G': (11, 5, 3), 'H': (8, 2, 4),
}
BUDGET = 600
s = json.load(open('schedule.json'))['schedule']
ok = True
def chk(label, cond):
    global ok
    print(("PASS  " if cond else "FAIL  ") + label)
    ok = ok and cond

chk("exactly the eight jobs, each once", sorted(s) == sorted(DATA))
total = 0
rows = []
for j in sorted(DATA):
    r, p, w = DATA[j]
    st, ct = s[j]['start'], s[j]['completion']
    chk("%s: start %g >= release %g" % (j, st, r), st >= r)
    chk("%s: completion %g == start + duration %g" % (j, ct, p), ct == st + p)
    total += w * ct
    rows.append((j, st, ct, w, w * ct))
iv = sorted((s[j]['start'], s[j]['completion']) for j in s)
chk("no overlapping intervals", all(iv[i][1] <= iv[i+1][0] for i in range(len(iv)-1)))
chk("total weighted completion cost %g <= %d" % (total, BUDGET), total <= BUDGET)
print()
print("%-4s %8s %11s %7s %10s" % ("job","start","completion","weight","w*C"))
for j, st, ct, w, wc in rows:
    print("%-4s %8g %11g %7g %10g" % (j, st, ct, w, wc))
print("%-4s %8s %11s %7s %10g" % ("TOTAL","","","",total))
print()
print("VERDICT:", "ALL CHECKS PASSED" if ok else "VERIFICATION FAILED")
raise SystemExit(0 if ok else 1)
