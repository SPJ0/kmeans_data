"""Freeze the measured-run manifest (run once, after the smoke test, before any measured play).

  python3 -m controller.make_manifest --seed 20260923 --out manifest.json

Run order is a seeded permutation of the 10 (game, rep) slots; the seed controls ONLY the order.
The manifest records sha256 hashes of every file that shapes the player's experience or the
controller's behaviour; controller.schedule refuses to run if any of them changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from datetime import datetime, timezone

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN = [
    "protocol.md",
    "prompts/player_prompt_v1.txt", "prompts/creative_block_v1.txt", "prompts/continuation_v1.txt",
    "controller/digclient.py", "controller/gamectl.py", "controller/relay.py", "controller/runner.py",
    "controller/sandbox.py", "controller/netfilter.py", "controller/netbridge.py", "controller/schedule.py",
    "grader/grade.py",
]


def sha(p):
    with open(os.path.join(PROJECT, p), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--games", nargs="+", default=["P-16", "P-19"])
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(PROJECT, "manifest.json"))
    a = ap.parse_args(argv)
    if os.path.exists(a.out):
        raise SystemExit(f"{a.out} exists; a frozen manifest is never regenerated in place")
    slots = [(g, r) for g in a.games for r in range(1, a.reps + 1)]
    order = list(range(len(slots)))
    random.Random(a.seed).shuffle(order)
    attempts = []
    for pos, i in enumerate(order, start=1):
        g, r = slots[i]
        attempts.append({"id": f"M{pos:02d}", "order": pos, "game": g, "rep": r, "phase": "measured"})
    manifest = {
        "version": "v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scheduling_seed": a.seed,
        "scheduling_note": "random.Random(seed).shuffle over slots [(game, rep) for game in games for rep in 1..reps]; order only",
        "games": a.games, "reps_per_game": a.reps, "max_concurrent": 2, "phase_dir": "measured",
        "attempt_seconds": 3600, "max_replacements": 2,
        "attempts": attempts, "replacements": [],
        "frozen_files_sha256": {p: sha(p) for p in FROZEN},
    }
    with open(a.out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
