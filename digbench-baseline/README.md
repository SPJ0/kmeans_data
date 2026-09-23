# DiG-bench vanilla-agent baseline (P-16, P-19)

This directory is a small, reproducible apparatus for a **single-condition** baseline. Headless Claude Code (`claude-opus-5-5`, CLI 2.1.280, effort `xhigh`, auto permission mode) plays DiG-bench games P-16 and P-19 five times each, with a 60-minute elapsed-time cap per attempt. Scores come only from the trusted controller's logs of server responses.

The full specification is in [`protocol.md`](protocol.md). Once it is frozen, `manifest.json` pins the protocol's sha256 and the sha256 of every file that shapes the player's experience.

```
protocol.md          frozen protocol (v1)
manifest.json        frozen 10-attempt manifest (created after the smoke test)
prompts/             fixed player prompt, creative-mode block, neutral continuation
controller/          digclient (API), gamectl (trusted controller), relay (player game tool),
                     runner (one attempt), sandbox/netfilter/netbridge (isolation), schedule,
                     smoke, make_manifest
grader/grade.py      automatic scoring + integrity checks + contamination audit
tests/               fixture server, apparatus tests, runner-policy tests, sandbox probes
runs/synthetic/      apparatus checks against the local fixture game (never results)
runs/smoke/          excluded P-1 smoke test + live API contract audit
runs/measured/       the 10 attempts (trusted/events.jsonl is the raw record)
runs/replacement/    linked replacements, if any (max 2)
reports/             generated tables + written report
```

## Requirements

- Root in this cloud container. It provides `unshare`, `setpriv` and namespaces.
- Python 3.11 standard library only.
- Claude Code CLI 2.1.280 authenticated by the container.
- Network access to `api.digbench.ai` for the manager side only. Players can never reach it; see `controller/netfilter.py`.
- A DiG-bench token in the manager's environment as `DIGBENCH_API_TOKEN`. Only the controller reads it, and it never enters player sandboxes or logs.

## Reproduce

```bash
cd digbench-baseline

# 1. Local validation (no model, no network except the sandbox probe's pypi check)
python3 -m unittest tests.test_apparatus tests.test_runner_policy tests.test_sandbox -v

# 2. Optional synthetic real-model check (fixture game; excluded from results)
python3 -m tests.integration_synthetic --seconds 300 --label S03

# 3. Excluded P-1 smoke test (<=10 min) + live API contract audit
python3 -m controller.smoke --seconds 600

# 4. Freeze: flip protocol.md status to FROZEN (commit), then generate the manifest once
python3 -m controller.make_manifest --seed 20260923

# 5. Measured runs (<=2 concurrent; resumable; long-lived background process)
nohup python3 -m controller.schedule --manifest manifest.json > runs/measured/scheduler.out 2>&1 &

# 6. Grade (tables are generated only from trusted logs)
python3 -m grader.grade --manifest manifest.json --runs runs --incidents runs/measured/incidents.json --out reports/generated
```

## Resume

`controller.schedule` skips any attempt that already has `trusted/events.jsonl`.

- **Interrupted scheduler.** If the scheduler died, rerun the same command. Finished attempts are kept. An attempt with a trusted log but no `attempt.json` was interrupted mid-run. It is reported as such and never silently rerun; only the incident policy in `protocol.md` §8 can authorize a linked replacement, via `replacements.json`.
- **Protocol changes.** If the protocol must change, create `protocol_v2.md` and a new manifest. Never edit the frozen files: the scheduler refuses to run if their hashes differ.
