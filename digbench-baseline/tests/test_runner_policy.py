"""SYNTHETIC runner-policy tests: real sandbox + controller + fixture server, with a scripted fake
player instead of the model. Exercises the fixed continuation policy, harness-exit resumption, and
the hard deadline kill of a player that ignores SIGTERM and leaves background children.

  cd digbench-baseline && python3 -m unittest tests.test_runner_policy -v     (needs root)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

from controller import runner  # noqa: E402
from grader import grade  # noqa: E402
from tests.fakeserver import FakeBench  # noqa: E402


class RunnerPolicyTests(unittest.TestCase):
    def run_mode(self, mode, seconds=60.0):
        tmp = tempfile.mkdtemp()
        src = open(os.path.join(HERE, "fake_player.py")).read().replace("__MODE__", mode)
        fake = os.path.join(tmp, "fake_player.py")
        with open(fake, "w") as f:
            f.write(src)
        runner.TEST_PLAYER_BIN = fake
        os.environ["DIGBENCH_API_TOKEN"] = "synthetic-not-a-real-token"
        fb = FakeBench(game_kwargs={"levels": 3, "steps": 50, "lives": 3}).start()
        run_dir = os.path.join(tmp, "synthetic", mode)
        ns = argparse.Namespace(attempt_id=f"P-{mode}", game="SYNTH-1", rep=0, phase="synthetic",
                                run_dir=run_dir, server=fb.url, attempt_seconds=seconds,
                                manifest_sha256=None, slot=0)
        try:
            meta = runner.run_attempt(ns)
        finally:
            runner.TEST_PLAYER_BIN = None
            fb.stop()
        evs = [json.loads(l) for l in open(os.path.join(run_dir, "trusted", "events.jsonl"))]
        return meta, evs, run_dir, tmp

    def test_idle_player_gets_one_continuation_then_declines(self):
        meta, evs, rd, tmp = self.run_mode("idle")
        self.assertEqual(meta["stop_reason"], "player_declined_after_continuation")
        self.assertEqual(meta["counts"]["player_continuations"], 1)
        kinds = [e.get("message_kind") for e in evs if e["kind"] == "dispatch"]
        self.assertEqual(kinds, ["initial", "continuation"])
        shutil.rmtree(tmp, ignore_errors=True)

    def test_acting_player_gets_two_continuations(self):
        meta, evs, rd, tmp = self.run_mode("act_each_turn")
        self.assertEqual(meta["stop_reason"], "player_ended_turn_after_continuations")
        self.assertEqual(meta["counts"]["player_continuations"], 2)
        self.assertEqual(sum(1 for e in evs if e["kind"] == "step_result"), 3)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_harness_exit_is_resumed_once_and_logged(self):
        meta, evs, rd, tmp = self.run_mode("crash_once")
        self.assertEqual(meta["counts"]["resumes"], 1)
        self.assertTrue(any(e["kind"] == "incident" and e.get("type") == "harness_exit_resume" for e in evs))
        launches = [e for e in evs if e["kind"] == "player_launch"]
        self.assertEqual([l["resume"] for l in launches], [False, True])
        self.assertIn("--resume", launches[1]["argv"])
        self.assertEqual(meta["stop_reason"], "player_ended_turn_after_continuations")
        shutil.rmtree(tmp, ignore_errors=True)

    def test_deadline_kills_whole_player_tree(self):
        meta, evs, rd, tmp = self.run_mode("hang", seconds=8.0)
        self.assertEqual(meta["stop_reason"], "time_limit")
        killed = next(e for e in evs if e["kind"] == "player_killed")
        self.assertLess(killed["t"], 8.0 + 5.0)
        self.assertFalse(any(e["kind"] == "step_send" and e["t"] > 8.0 for e in evs))
        time.sleep(1.5)
        hb = os.path.join(rd, "player_artifacts", "work", "heartbeat.txt")
        self.assertTrue(os.path.exists(hb))
        # No sandbox process survives the kill (the background heartbeat child included).
        ps = subprocess.run(["pgrep", "-f", "heartbeat.txt"], capture_output=True, text=True)
        self.assertEqual(ps.stdout.strip(), "", f"survivors: {ps.stdout}")
        rec = grade.derive(rd)
        self.assertEqual(rec["stop_reason"], "time_limit")
        self.assertEqual(rec["checkpoints"]["900"]["coverage"], "final")
        self.assertFalse(rec["checks"]["step_sent_after_deadline"])
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
