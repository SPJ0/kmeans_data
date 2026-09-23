"""SYNTHETIC local stand-in for the DiG-bench Agent API, for apparatus tests ONLY.

It mimics the documented protocol (POST /api/agent/sessions, POST .../step with idempotent
step_index, 409 on index mismatch, invalid_action no-ops, GET .../sessions/{id}) with a trivial
made-up corridor game. It is not a DiG-bench game and nothing it produces is a result. Every
session it creates carries ``"synthetic": true`` and a ``SYNTH-`` game name.

Fault injection (per server instance): ``faults`` dict with keys
  drop_after_apply: set of step indices whose response is dropped AFTER the step is applied
  fail_5xx:         set of step indices answered once with HTTP 503 BEFORE applying
  delay:            {step_index: seconds} delay before answering (applied first)
  create_hang_s:    seconds to hang on POST /sessions (to provoke a client timeout)
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class CorridorGame:
    def __init__(self, levels=3, steps=6, lives=2, creative=True):
        self.max_level, self.steps_per_level, self.creative = levels, steps, creative
        self.level, self.lives, self.pos, self.steps = 1, lives, 0, steps
        self.status, self.mode, self.transition = "in_progress", "survival", None
        self.saved = None
        self.applied = 0

    def length(self):
        return 2 + self.level

    def state(self):
        obs = "[" + "".join("@" if i == self.pos else ("★" if i == self.length() else "·")
                            for i in range(self.length() + 1)) + "]"
        if self.mode == "creative":
            obs = "creative\n" + obs
        acts = ["l", "r"] + (["/"] if self.creative else [])
        st = {"observation": obs, "level": self.level, "max_level": self.max_level,
              "lives_left": self.lives, "steps_remaining": self.steps, "status": self.status,
              "done": self.status != "in_progress", "actions": [] if self.status != "in_progress" else acts,
              "transition": self.transition}
        if self.creative:
            st["mode"] = self.mode
            st["creative_toggle"] = "/"
        return st

    def apply(self, a):
        self.applied += 1
        self.transition = None
        if a == "/":
            if self.mode == "survival":
                self.saved = (self.pos, self.steps)
                self.mode, self.pos = "creative", 0
            else:
                self.mode = "survival"
                self.pos, self.steps = self.saved
            return
        self.pos = max(0, self.pos - 1) if a == "l" else self.pos + 1
        if self.mode == "creative":
            self.pos = min(self.pos, self.length())
            return
        self.steps -= 1
        if self.pos >= self.length():
            if self.level == self.max_level:
                self.status = "completed"
                return
            self.transition = f"Level {self.level} cleared — advancing to level {self.level + 1}."
            self.level += 1
            self.pos, self.steps = 0, self.steps_per_level
        elif self.steps <= 0:
            self.lives -= 1
            if self.lives <= 0:
                self.status = "game_over"
                return
            self.transition = f"Level {self.level} failed — restarting level {self.level}."
            self.pos, self.steps = 0, self.steps_per_level


class FakeBench:
    def __init__(self, faults=None, game_kwargs=None):
        self.faults = faults or {}
        self.game_kwargs = game_kwargs or {}
        self.sessions = {}
        self.creates = 0
        self.lock = threading.Lock()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self._failed_once = set()

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.httpd.shutdown()

    def _handler(self):
        bench = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, code, obj):
                data = json.dumps(obj, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _auth(self):
                if not self.headers.get("Authorization", "").startswith("Bearer "):
                    self._json(401, {"error": "unauthorized"})
                    return False
                return True

            def do_GET(self):
                if not self._auth():
                    return
                if self.path == "/api/agent/games":
                    return self._json(200, {"games": ["SYNTH-1"]})
                if self.path.startswith("/api/agent/sessions/"):
                    sid = self.path.rsplit("/", 1)[-1]
                    s = bench.sessions.get(sid)
                    if not s:
                        return self._json(404, {"error": "no session"})
                    return self._json(200, {"session_id": sid, "step_index": s["idx"], "state": s["game"].state()})
                self._json(404, {"error": "not found"})

            def do_POST(self):
                if not self._auth():
                    return
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path == "/api/agent/sessions":
                    hang = bench.faults.get("create_hang_s")
                    with bench.lock:
                        bench.creates += 1
                        sid = str(uuid.uuid4())
                        g = CorridorGame(**bench.game_kwargs)
                        bench.sessions[sid] = {"game": g, "idx": 0, "last": None}
                    if hang:
                        time.sleep(hang)
                    return self._json(200, {"session_id": sid, "game": body.get("game"), "seed": 12345,
                                            "framework_version": "synthetic-0", "synthetic": True,
                                            "description": "SYNTHETIC test game: reach the star.",
                                            "state": g.state(), "step_index": 0, "done": False})
                if self.path.endswith("/step"):
                    sid = self.path.split("/")[-2]
                    s = bench.sessions.get(sid)
                    if not s:
                        return self._json(404, {"error": "no session"})
                    idx, action = body.get("step_index"), body.get("action")
                    d = bench.faults.get("delay", {}).get(idx)
                    if d:
                        time.sleep(d)
                    with bench.lock:
                        if idx in bench.faults.get("fail_5xx", set()) and idx not in bench._failed_once:
                            bench._failed_once.add(idx)
                            return self._json(503, {"error": "transient"})
                        if s["last"] is not None and idx == s["last"][0]:
                            return self._json(200, s["last"][1])      # idempotent replay
                        if idx != s["idx"] + 1:
                            return self._json(409, {"error": f"wrong index: expected {s['idx'] + 1}"})
                        g = s["game"]
                        st = g.state()
                        if g.status != "in_progress" or action not in st["actions"]:
                            resp = {"state": copy.deepcopy(st), "step_index": s["idx"], "invalid_action": True}
                            return self._json(200, resp)
                        g.apply(action)
                        s["idx"] = idx
                        resp = {"state": g.state(), "step_index": idx, "invalid_action": False}
                        s["last"] = (idx, resp)
                        drop = idx in bench.faults.get("drop_after_apply", set())
                        if drop:
                            bench.faults["drop_after_apply"] = bench.faults["drop_after_apply"] - {idx}
                    if drop:
                        self.connection.shutdown(2)   # applied, but the response is lost
                        return
                    return self._json(200, resp)
                self._json(404, {"error": "not found"})

        return H
