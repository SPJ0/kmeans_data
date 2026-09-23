"""SYNTHETIC end-to-end harness check: a real sandboxed Claude Code player drives the local fixture
game (tests/fakeserver.py) through the MCP bridge. Validates launch, auth inside the sandbox, MCP
wiring, stream-json dispatch, continuations, the deadline kill, and artifact collection.
Output goes to runs/synthetic/ and is never eligible for measured tables.

  python3 -m tests.integration_synthetic --seconds 300 [--levels 3] [--label S01]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from controller import runner  # noqa: E402
from tests.fakeserver import FakeBench  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=300)
    p.add_argument("--levels", type=int, default=3)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--label", default="S01")
    a = p.parse_args()
    fb = FakeBench(game_kwargs={"levels": a.levels, "steps": a.steps, "lives": 3}).start()
    os.environ["DIGBENCH_API_TOKEN"] = "synthetic-not-a-real-token"
    run_dir = os.path.join(PROJECT, "runs", "synthetic", f"{a.label}-{time.strftime('%Y%m%dT%H%M%S')}")
    args = runner.main.__wrapped__ if hasattr(runner.main, "__wrapped__") else None  # noqa: F841
    ns = argparse.Namespace(attempt_id=a.label, game="SYNTH-1", rep=0, phase="synthetic", run_dir=run_dir,
                            server=fb.url, attempt_seconds=a.seconds, manifest_sha256=None, slot=0)
    meta = runner.run_attempt(ns)
    fb.stop()
    print(json.dumps({k: meta.get(k) for k in ("attempt_id", "session_id", "stop_reason", "counts",
                                               "reported_models_at_init", "final_state")}, indent=2,
                     ensure_ascii=False))
    print("run_dir:", run_dir)


if __name__ == "__main__":
    main()
