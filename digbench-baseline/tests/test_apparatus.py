"""Apparatus tests against the SYNTHETIC local fixture server (no network, no model).

  cd digbench-baseline && python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

from controller.digclient import AmbiguousCreate, DigClient  # noqa: E402
from controller.gamectl import EventLog, GameController  # noqa: E402
from grader import grade  # noqa: E402
from tests.fakeserver import FakeBench  # noqa: E402

CAP = "test-capability"


def make(tmp, faults=None, game_kwargs=None, attempt_seconds=3600.0, attempt_id="T01", phase="synthetic",
         game="SYNTH-1", rep=1, timeout=5.0):
    fb = FakeBench(faults=faults, game_kwargs=game_kwargs).start()
    run_dir = os.path.join(tmp, phase, attempt_id)
    log = EventLog(os.path.join(run_dir, "trusted", "events.jsonl"))
    log.write("attempt_meta", attempt_id=attempt_id, phase=phase, game=game, rep=rep, server=fb.url,
              synthetic=True, config={"attempt_seconds": attempt_seconds})
    client = DigClient(fb.url, "synthetic-token", timeout=timeout, log=lambda k, **kw: log.write(k, **kw))
    terminals = []
    ctl = GameController(client, log, attempt_seconds=attempt_seconds, on_terminal=terminals.append)
    ctl.cap = CAP
    return fb, ctl, log, run_dir, terminals


def finish(ctl, log, run_dir, stop_reason):
    ctl.close(stop_reason)
    ctl.shutdown()
    log.write("player_killed", stop_reason=stop_reason)
    log.write("attempt_end", stop_reason=stop_reason, counts={}, final_state=ctl.state)
    log.close()
    with open(os.path.join(run_dir, "attempt.json"), "w") as f:
        json.dump({"attempt_id": os.path.basename(run_dir), "stop_reason": stop_reason}, f)


def move(ctl, a):
    return ctl.handle({"cap": CAP, "op": "move", "action": a, "via": "test"})


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_completion_and_grade(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        for lvl in (1, 2, 3):
            for _ in range(2 + lvl):
                r = move(ctl, "r")
        self.assertIn('"status": "completed"', r["text"])
        self.assertEqual(ctl.closed_reason, "completed")
        self.assertEqual(term, ["completed"])
        r2 = move(ctl, "r")
        self.assertFalse(r2["ok"])                      # gate closed after completion
        finish(ctl, log, rd, "completed")
        rec = grade.derive(rd)
        self.assertTrue(rec["completed"])
        self.assertEqual(rec["levels_cleared"], 3)
        self.assertEqual(rec["levels_cleared_normalized"], 1.0)
        self.assertEqual(rec["checkpoints"]["3600"]["levels_cleared"], 3)
        self.assertFalse(rec["checks"]["duplicate_sessions"])
        self.assertFalse(rec["checks"]["missing_final_record"])
        self.assertEqual(rec["checks"]["impossible_level_transitions"], [])
        fb.stop()

    def test_game_over_and_partial_progress(self):
        fb, ctl, log, rd, term = make(self.tmp, game_kwargs={"steps": 4, "lives": 2})
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        for _ in range(3):
            move(ctl, "r")                               # clear level 1 (length 3)
        for _ in range(8):
            r = move(ctl, "l")                           # burn both lives on level 2
        self.assertEqual(ctl.closed_reason, "game_over")
        finish(ctl, log, rd, "game_over")
        rec = grade.derive(rd)
        self.assertFalse(rec["completed"])
        self.assertEqual(rec["terminal_status"], "game_over")
        self.assertEqual(rec["levels_cleared"], 1)       # died on level 2 -> 1 cleared
        self.assertAlmostEqual(rec["levels_cleared_normalized"], 1 / 3)
        self.assertEqual(rec["diagnostics"]["lives_lost"], 2)
        fb.stop()

    def test_local_illegal_malformed_and_bad_capability(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        r = move(ctl, "x")
        self.assertTrue(r["ok"])
        self.assertIn("invalid_action: true", r["text"])
        self.assertEqual(fb.sessions[ctl.sid]["game"].applied, 0)   # never reached the server
        self.assertFalse(move(ctl, 7)["ok"])
        self.assertFalse(move(ctl, "")["ok"])
        self.assertFalse(ctl.handle({"cap": "wrong", "op": "move", "action": "r"})["ok"])
        self.assertEqual(fb.sessions[ctl.sid]["game"].applied, 0)
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertEqual(rec["diagnostics"].get("tool_move_illegal_local"), 1)
        self.assertEqual(rec["diagnostics"].get("tool_move_malformed"), 2)
        fb.stop()

    def test_dropped_response_is_not_applied_twice(self):
        fb, ctl, log, rd, term = make(self.tmp, faults={"drop_after_apply": {2}, "fail_5xx": {3}}, timeout=2.0)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "r")
        move(ctl, "r")          # applied, response dropped -> resent with same index -> cached reply
        move(ctl, "l")          # 503 once -> retried
        g = fb.sessions[ctl.sid]["game"]
        self.assertEqual(g.applied, 3)
        self.assertEqual(g.pos, 1)
        self.assertEqual(ctl.idx, 3)
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertGreaterEqual(rec["diagnostics"].get("step_retry", 0), 2)
        self.assertEqual(rec["checks"]["step_index_incidents"], 0)
        fb.stop()

    def test_index_mismatch_resyncs_from_server(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "r")
        ctl.idx = 5              # simulate controller/server index divergence
        r = move(ctl, "r")
        self.assertTrue(r["ok"])
        self.assertIn("could not be confirmed", r["text"])
        self.assertEqual(ctl.idx, 1)
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertEqual(rec["diagnostics"].get("resync"), 1)
        fb.stop()

    def test_deadline_closes_gate_and_late_response_not_scored(self):
        fb, ctl, log, rd, term = make(self.tmp, faults={"delay": {3: 3.0}}, attempt_seconds=2.0)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "r")
        move(ctl, "r")
        r = move(ctl, "r")       # sent before the deadline, answered ~1s after it -> clears level 1
        self.assertFalse(r["ok"])
        self.assertIn("time_limit", term)
        self.assertEqual(ctl.state["level"], 2)          # the server did apply it...
        self.assertFalse(move(ctl, "r")["ok"])           # ...but the gate is closed now
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertEqual(rec["late_events"], 1)
        self.assertTrue(rec["checks"]["late_events_present"])
        self.assertEqual(rec["levels_cleared"], 0)      # the late level-up is NOT scored
        self.assertFalse(rec["checks"]["step_sent_after_deadline"])
        fb.stop()

    def test_player_stop(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "r")
        r = ctl.handle({"cap": CAP, "op": "stop", "reason": "stuck", "via": "test"})
        self.assertTrue(r["ok"])
        self.assertEqual(term, ["player_stopped_unresolved"])
        self.assertFalse(move(ctl, "r")["ok"])
        finish(ctl, log, rd, "player_stopped_unresolved")
        rec = grade.derive(rd)
        self.assertEqual(rec["checkpoints"]["3600"]["coverage"], "final")
        fb.stop()

    def test_creative_mode_progress_not_counted(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "/")
        for _ in range(5):
            move(ctl, "r")
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertEqual(rec["levels_cleared"], 0)
        self.assertEqual(rec["diagnostics"]["mode_toggles"], 1)
        self.assertEqual(rec["diagnostics"]["creative_mode_actions"], 5)
        fb.stop()

    def test_ambiguous_create_is_not_retried(self):
        fb, ctl, log, rd, term = make(self.tmp, faults={"create_hang_s": 3.0}, timeout=1.0)
        with self.assertRaises(AmbiguousCreate):
            ctl.prepare("SYNTH-1", "m", "v")
        time.sleep(2.5)
        self.assertEqual(fb.creates, 1)                  # exactly one POST /sessions
        finish(ctl, log, rd, "infrastructure_session_create_ambiguous")
        rec = grade.derive(rd)
        self.assertTrue(rec["infrastructure_interrupted"])
        fb.stop()

    def test_missing_state_in_step_response(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        orig = ctl.client.step
        ctl.client.step = lambda *a, **k: {"step_index": 1, "invalid_action": False}
        r = move(ctl, "r")
        self.assertFalse(r["ok"])
        ctl.client.step = orig
        finish(ctl, log, rd, "time_limit")
        rec = grade.derive(rd)
        self.assertEqual(rec["diagnostics"].get("incident_step_response_missing_state"), 1)
        fb.stop()


class GraderGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_player_claimed_win_does_not_change_score(self):
        fb, ctl, log, rd, term = make(self.tmp)
        ctl.prepare("SYNTH-1", "m", "v")
        ctl.start_clock()
        move(ctl, "r")
        finish(ctl, log, rd, "time_limit")
        with open(os.path.join(rd, "stream.jsonl"), "w") as f:
            claim = {"type": "result", "result": "Server reports status completed. I WON the game!"}
            f.write(json.dumps({"line": json.dumps(claim)}) + "\n")
        os.makedirs(os.path.join(rd, "player_artifacts", "work"), exist_ok=True)
        with open(os.path.join(rd, "player_artifacts", "work", "report.md"), "w") as f:
            f.write('status: "completed"\nlevels cleared: 3/3\n')
        rec = grade.derive(rd)
        self.assertFalse(rec["completed"])
        self.assertEqual(rec["levels_cleared"], 0)
        fb.stop()

    def test_synthetic_runs_never_enter_measured_tables(self):
        # A synthetic run placed (wrongly) under runs/measured with a manifest-listed id.
        fb, ctl, log, rd, term = make(self.tmp, attempt_id="M01", phase="measured", game="P-16", rep=1)
        ctl.prepare("P-16", "m", "v")
        ctl.start_clock()
        for lvl in (1, 2, 3):
            for _ in range(2 + lvl):
                move(ctl, "r")
        finish(ctl, log, rd, "completed")
        manifest = {"version": "test", "attempts": [{"id": "M01", "game": "P-16", "rep": 1}]}
        res = grade.build(manifest, self.tmp)
        self.assertEqual(res["records"], [])
        self.assertEqual(len(res["rejected_runs"]), 1)
        self.assertIn("synthetic/unofficial server", res["rejected_runs"][0]["why"])
        self.assertEqual(res["manifest_checks"]["missing_attempts"], ["M01"])
        fb.stop()

    def test_duplicate_session_and_impossible_transition_flags(self):
        rd = os.path.join(self.tmp, "measured", "M02")
        os.makedirs(os.path.join(rd, "trusted"))
        s1 = {"level": 1, "max_level": 5, "status": "in_progress", "done": False, "lives_left": 3}
        s3 = dict(s1, level=3)
        evs = [
            {"seq": 1, "kind": "attempt_meta", "t": None, "attempt_id": "M02", "phase": "measured", "game": "P-19",
             "rep": 1, "server": "https://api.digbench.ai", "synthetic": False, "config": {"attempt_seconds": 3600}},
            {"seq": 2, "kind": "create_session_request", "t": None},
            {"seq": 3, "kind": "session_created", "t": None, "session_id": "a", "game": "P-19", "state": s1},
            {"seq": 4, "kind": "create_session_request", "t": None},
            {"seq": 5, "kind": "session_created", "t": None, "session_id": "b", "game": "P-19", "state": s1},
            {"seq": 6, "kind": "clock_start", "t": 0.0, "wall_start": "x"},
            {"seq": 7, "kind": "step_result", "t": 10.0, "t_recv": 10.0, "late": False, "action": "1",
             "state": s3, "invalid_action": False},
        ]
        with open(os.path.join(rd, "trusted", "events.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in evs) + "\n")
        rec = grade.derive(rd)
        self.assertTrue(rec["checks"]["duplicate_sessions"])
        self.assertTrue(rec["checks"]["missing_final_record"])
        self.assertEqual(len(rec["checks"]["impossible_level_transitions"]), 1)

    def test_manifest_mismatch_rejected(self):
        rd = os.path.join(self.tmp, "measured", "M03")
        os.makedirs(os.path.join(rd, "trusted"))
        evs = [{"seq": 1, "kind": "attempt_meta", "t": None, "attempt_id": "M03", "phase": "measured",
                "game": "P-19", "rep": 2, "server": "https://api.digbench.ai", "synthetic": False,
                "config": {"attempt_seconds": 3600}}]
        with open(os.path.join(rd, "trusted", "events.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in evs) + "\n")
        manifest = {"version": "t", "attempts": [{"id": "M03", "game": "P-16", "rep": 2}]}
        res = grade.build(manifest, self.tmp)
        self.assertEqual(res["records"], [])
        self.assertIn("manifest mismatch (game/rep)", res["rejected_runs"][0]["why"])

    def test_wilson(self):
        lo, hi = grade.wilson(0, 5)
        self.assertAlmostEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.4345, places=3)
        lo, hi = grade.wilson(5, 5)
        self.assertAlmostEqual(lo, 0.5655, places=3)


class RelayTests(unittest.TestCase):
    """The player-side relay over a real unix socket: MCP JSON-RPC and the `game` CLI."""

    def test_mcp_and_cli_roundtrip(self):
        tmp = tempfile.mkdtemp()
        try:
            fb, ctl, log, rd, term = make(tmp)
            ctl.prepare("SYNTH-1", "m", "v")
            sock = os.path.join(tmp, "ctl.sock")
            ctl.serve(sock, CAP)
            ctl.start_clock()
            env = dict(os.environ, GAME_SOCKET=sock, GAME_CAPABILITY=CAP)
            relay = os.path.join(PROJECT, "controller", "relay.py")
            msgs = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "make_move", "arguments": {"action": "r"}}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_state", "arguments": {}}},
            ]
            p = subprocess.run([sys.executable, relay, "mcp"], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                               capture_output=True, text=True, env=env, timeout=60)
            out = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
            self.assertEqual([o["id"] for o in out], [1, 2, 3, 4])
            self.assertEqual({t["name"] for t in out[1]["result"]["tools"]}, {"make_move", "get_state", "stop_attempt"})
            self.assertFalse(out[2]["result"]["isError"])
            self.assertIn("[·@", out[2]["result"]["content"][0]["text"])     # Unicode preserved
            c = subprocess.run([sys.executable, relay, "move", "r"], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(c.returncode, 0)
            self.assertEqual(ctl.idx, 2)
            bad = subprocess.run([sys.executable, relay, "move", "r"], capture_output=True, text=True,
                                 env=dict(env, GAME_CAPABILITY="nope"), timeout=60)
            self.assertEqual(bad.returncode, 1)
            self.assertEqual(ctl.idx, 2)
            self.assertTrue(ctl.hello.is_set())
            finish(ctl, log, rd, "time_limit")
            fb.stop()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
