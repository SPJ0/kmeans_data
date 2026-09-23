# Handoff: continuing the DiG-bench vanilla baseline in a new session

Use this if the study continues in a fresh Claude Code cloud session. That will be necessary because environment variables such as `DIGBENCH_API_TOKEN` only reach new sessions.

## Current state

- **Apparatus.** Built and validated locally on branch `claude/dig-bench-vanilla-baseline-1sp09q`. See `README.md` and `protocol.md`.
- **Live runs.** None have been made. Two things blocked them:
  1. the environment's network policy denied `api.digbench.ai` and `digbench.ai` (the proxy returned 403);
  2. the environment had no `DIGBENCH_API_TOKEN`.
- **Protocol.** `protocol.md` is v1 and still marked DRAFT. It is frozen by generating `manifest.json` after the smoke test.

## Steps for the new manager session (as root, from the repo root)

1. Confirm access without printing the token:

   ```bash
   [ -n "$DIGBENCH_API_TOKEN" ] && echo token ok
   curl -sS -o /dev/null -w '%{http_code}\n' https://api.digbench.ai/api/agent/games
   ```

   The curl should return 401 or 200, not 000 or a proxy 403.

2. Re-run the local validation:

   ```bash
   cd digbench-baseline && python3 -m unittest tests.test_apparatus tests.test_runner_policy tests.test_sandbox -v
   ```

   These use the root-only namespace features.

3. Run the excluded smoke test:

   ```bash
   python3 -m controller.smoke --seconds 600
   ```

   Then read `runs/smoke/*/api_audit.json`. Check that P-1, P-16 and P-19 are listed and note the tiers if the server returns them. Also check whether `GET /sessions/{id}` exists, whether idempotent replay held, and whether seeds are returned. Finally check that the player saw the observation, acted, and was stopped by the controller.

4. Before freezing, read the live API documentation at digbench.ai/api. The manager may read it; players may not. Check two things:
   - whether sessions or `model_name` are published on a public leaderboard or playback page, and if so, ask Josh before running;
   - whether a client can request a seed.

5. If the smoke test shows a real apparatus bug, fix it and re-run the tests and smoke test. This is still pre-freeze, so it needs no new protocol version. Then set `protocol.md` Status to FROZEN, commit, and run:

   ```bash
   python3 -m controller.make_manifest --seed 20260923
   ```

   Commit `manifest.json`.

6. Launch the measured runs:

   ```bash
   nohup python3 -m controller.schedule --manifest manifest.json > runs/measured/scheduler.out 2>&1 &
   ```

   At most 2 run concurrently. Watch `runs/measured/scheduler.log`. The run takes about 5 h or less.

7. Grade:

   ```bash
   python3 -m grader.grade --manifest manifest.json --runs runs --incidents runs/measured/incidents.json --out reports/generated
   ```

   Then do three things:
   - review the contamination flags;
   - have an independent reviewer spot-check the scoring against raw `trusted/events.jsonl`;
   - write `reports/report.md`.

Never pass manager research, other attempts' results or strategy text into player prompts or files.
