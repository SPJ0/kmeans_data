import json, itertools, time
jobs = json.load(open('jobs.json'))
names = sorted(jobs)
t0 = time.time()
best = None
for perm in itertools.permutations(names):
    t = 0; cost = 0
    for j in perm:
        d = jobs[j]
        s = max(t, d['r']); c = s + d['p']; t = c
        cost += d['w'] * c
    if best is None or cost < best[0]:
        best = (cost, perm)
cost, perm = best
t = 0; sched = {}
for j in perm:
    d = jobs[j]; s = max(t, d['r']); c = s + d['p']; t = c
    sched[j] = {"start": s, "completion": c}
json.dump({"order": list(perm), "schedule": sched}, open('schedule.json','w'), indent=2)
print("optimal cost:", cost, "order:", perm)
print("elapsed sec: %.2f" % (time.time()-t0))
