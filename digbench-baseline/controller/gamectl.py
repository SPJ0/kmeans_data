"""Trusted per-attempt game controller (manager side; runs outside the player sandbox).

Owns: the DiG-bench client (and therefore the credential), the one server session assigned to the
attempt, serialized idempotent stepping, the monotonic attempt clock and deadline gate, and the
append-only trusted event log that the grader reads. Serves the player-side relay over a unix
socket guarded by a per-attempt capability string. Contains no game-solving logic.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from datetime import datetime, timezone

from .digclient import AmbiguousCreate, BenchError, DeadlineExceeded, player_slice

ATTEMPT_SECONDS = 3600.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def format_state(slice_: dict, extra: dict | None = None) -> str:
    """Player-facing rendering: the official state slice as JSON (Unicode preserved), plus a
    rendered copy of the observation so multi-line screens are readable, plus controller extras
    (invalid_action / note / timing)."""
    parts = []
    obs = slice_.get("observation", "")
    parts.append("observation (rendered):\n" + (obs if isinstance(obs, str) else json.dumps(obs, ensure_ascii=False)))
    parts.append("state:\n" + json.dumps(slice_, ensure_ascii=False, indent=2))
    if extra:
        parts.append("\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in extra.items()))
    return "\n\n".join(parts)


class EventLog:
    """Append-only JSONL, fsync'd per event. Each event carries a sequence number, wall-clock
    UTC time, monotonic time, and time relative to the attempt clock (None before dispatch)."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._f = open(path, "a", encoding="utf-8")
        self._lock = threading.Lock()
        self._seq = 0
        self.t0: float | None = None

    def rel(self, mono: float | None = None) -> float | None:
        if self.t0 is None:
            return None
        return round((mono if mono is not None else time.monotonic()) - self.t0, 3)

    def write(self, kind: str, **data) -> dict:
        with self._lock:
            self._seq += 1
            mono = time.monotonic()
            ev = {"seq": self._seq, "kind": kind, "wall": utc_now(), "mono": round(mono, 3),
                  "t": self.rel(mono), **data}
            self._f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            self._f.flush()
            os.fsync(self._f.fileno())
            return ev

    def close(self):
        with self._lock:
            self._f.close()


class GameController:
    def __init__(self, client, log: EventLog, *, attempt_seconds: float = ATTEMPT_SECONDS,
                 on_terminal=None):
        self.client = client
        self.log = log
        self.attempt_seconds = attempt_seconds
        self.on_terminal = on_terminal or (lambda reason: None)
        self.lock = threading.Lock()          # serializes all game operations
        self.sid: str | None = None
        self.idx: int = 0
        self.state: dict = {}
        self.start: dict = {}
        self.t0: float | None = None
        self.deadline: float | None = None
        self.closed_reason: str | None = None
        self.terminal_t: float | None = None
        self.hello = threading.Event()
        self._timer: threading.Timer | None = None
        self._srv: socket.socket | None = None
        self.cap: str | None = None
        self.tool_requests = 0                # move/state/stop requests from the player

    # ------------------------------------------------------------------ setup (before clock)
    def prepare(self, game: str, model_name: str, model_version: str) -> dict:
        """Create exactly one server session. Never retried automatically: an ambiguous create is
        recorded as an infrastructure incident and re-raised for the runner's incident policy."""
        self.log.write("create_session_request", game=game, model_name=model_name,
                       model_version=model_version)
        try:
            start = self.client.create_session(game, model_name, model_version)
        except AmbiguousCreate as exc:
            self.log.write("incident", type="ambiguous_session_create", detail=str(exc)[:1000])
            raise
        except BenchError as exc:
            self.log.write("incident", type="session_create_rejected", detail=str(exc)[:1000])
            raise
        self.start = start
        self.sid = start.get("session_id")
        self.idx = start.get("step_index", 0) or 0
        self.state = start.get("state") or {}
        self.log.write("session_created", session_id=self.sid, game=start.get("game"),
                       seed=start.get("seed"), framework_version=start.get("framework_version"),
                       step_index=self.idx, description=start.get("description"),
                       state=self.state, response_keys=sorted(start.keys()),
                       extra={k: v for k, v in start.items()
                              if k not in ("state", "description", "session_id", "game", "seed",
                                           "framework_version", "step_index")})
        if self.sid is None or not isinstance(self.state, dict):
            self.log.write("incident", type="malformed_session_create")
            raise BenchError("session creation response missing session_id/state")
        return start

    def serve(self, sock_path: str, cap: str) -> None:
        self.cap = cap
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(sock_path)
        os.chmod(sock_path, 0o600)
        srv.listen(8)
        self._srv = srv
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()

    def _handle_conn(self, conn):
        try:
            conn.settimeout(30)
            buf = b""
            while not buf.endswith(b"\n") and len(buf) < 1_000_000:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
            conn.settimeout(None)
            try:
                req = json.loads(buf.decode("utf-8"))
                if not isinstance(req, dict):
                    raise ValueError("request is not an object")
            except ValueError as exc:
                self.log.write("tool_request_malformed", error=str(exc)[:300])
                resp = {"ok": False, "text": "Malformed request."}
            else:
                resp = self.handle(req)
            conn.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    # ------------------------------------------------------------------ clock
    def start_clock(self) -> tuple[float, str]:
        self.t0 = time.monotonic()
        self.log.t0 = self.t0
        self.deadline = self.t0 + self.attempt_seconds
        wall = utc_now()
        self.log.write("clock_start", wall_start=wall, attempt_seconds=self.attempt_seconds)
        self._timer = threading.Timer(self.attempt_seconds, self._on_deadline)
        self._timer.daemon = True
        self._timer.start()
        return self.t0, wall

    def remaining(self) -> float | None:
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - time.monotonic())

    def _timing(self) -> dict:
        rem = self.remaining()
        if rem is None:
            return {}
        return {"elapsed_s": round(time.monotonic() - self.t0, 1), "time_remaining_s": round(rem, 1)}

    def _on_deadline(self):
        # Deliberately NOT under self.lock: an in-flight step may hold the lock until its HTTP
        # timeout, and the deadline must close the gate and stop the player on time regardless.
        if self.closed_reason is None:
            self.closed_reason = "time_limit"
            self.log.write("gate_closed", reason="time_limit", state=self.state)
        self.on_terminal("time_limit")

    def close(self, reason: str):
        with self.lock:
            if self.closed_reason is None:
                self.closed_reason = reason
                self.log.write("gate_closed", reason=reason, state=self.state)

    def shutdown(self):
        if self._timer:
            self._timer.cancel()
        if self._srv:
            try:
                self._srv.close()
            except OSError:
                pass

    def game_done(self) -> bool:
        return bool(self.state.get("done")) or self.state.get("status") in ("completed", "game_over")

    # ------------------------------------------------------------------ request handling
    def handle(self, req: dict) -> dict:
        if req.get("cap") != self.cap:
            self.log.write("tool_request_rejected", why="bad_capability", op=str(req.get("op"))[:40])
            return {"ok": False, "text": "Not authorized."}
        op, via = req.get("op"), str(req.get("via", "?"))[:10]
        if op in ("move", "state", "stop"):
            self.tool_requests += 1
        if op == "hello":
            self.log.write("relay_hello", via=via)
            self.hello.set()
            return {"ok": True, "text": "ok"}
        if op == "state":
            return self._op_state(via)
        if op == "move":
            return self._op_move(req.get("action"), via)
        if op == "stop":
            return self._op_stop(str(req.get("reason", ""))[:2000], via)
        self.log.write("tool_request_malformed", op=str(op)[:40], via=via)
        return {"ok": False, "text": f"Unknown operation {op!r}."}

    def _closed_text(self) -> str:
        return {
            "time_limit": "The attempt's time limit has passed. The game tool is closed.",
            "completed": "The game is over (status: completed). The game tool is closed for moves.",
            "game_over": "The game is over (status: game_over). The game tool is closed for moves.",
            "player_stopped_unresolved": "You stopped this attempt. The game tool is closed.",
        }.get(self.closed_reason or "", f"The game tool is closed ({self.closed_reason}).")

    def _op_state(self, via: str) -> dict:
        with self.lock:
            self.log.write("tool_state", via=via, gate=self.closed_reason)
            if self.closed_reason == "time_limit":
                return {"ok": False, "text": self._closed_text()}
            extra = self._timing()
            if self.closed_reason:
                extra["note"] = self._closed_text()
            return {"ok": True, "text": format_state(player_slice(self.state), extra),
                    "data": player_slice(self.state)}

    def _op_stop(self, reason: str, via: str) -> dict:
        with self.lock:
            if self.closed_reason:
                self.log.write("tool_stop_ignored", via=via, gate=self.closed_reason, reason=reason)
                return {"ok": False, "text": self._closed_text()}
            self.closed_reason = "player_stopped_unresolved"
            self.terminal_t = self.log.rel()
            self.log.write("player_stop", via=via, reason=reason, state=self.state)
            self.log.write("gate_closed", reason="player_stopped_unresolved", state=self.state)
        self.on_terminal("player_stopped_unresolved")
        return {"ok": True, "text": "Recorded: you stopped this attempt unresolved. The game tool is now closed."}

    def _op_move(self, action, via: str) -> dict:
        terminal = None
        with self.lock:
            t_req = self.log.rel()
            if self.closed_reason:
                self.log.write("tool_move_rejected", via=via, action=str(action)[:100],
                               gate=self.closed_reason)
                return {"ok": False, "text": self._closed_text()}
            if self.t0 is None:
                self.log.write("tool_move_rejected", via=via, action=str(action)[:100], gate="clock_not_started")
                return {"ok": False, "text": "The attempt has not started yet."}
            if not isinstance(action, str) or action == "":
                self.log.write("tool_move_malformed", via=via, action=repr(action)[:100])
                return {"ok": False, "text": "`action` must be a non-empty string: exactly one of legal_actions."}
            legal = self.state.get("actions")
            if isinstance(legal, list) and legal and action not in legal:
                # Same local guard as the official harness: never send an action the player was not offered.
                self.log.write("tool_move_illegal_local", via=via, action=action[:100], legal=legal)
                sl = player_slice(self.state)
                sl.pop("transition", None)
                extra = {"invalid_action": True,
                         "note": f"{action!r} is not legal — pick one of legal_actions.", **self._timing()}
                return {"ok": True, "text": format_state(sl, extra), "data": sl}

            send_idx = self.idx + 1
            self.log.write("step_send", via=via, action=action, step_index=send_idx, t_req=t_req)
            try:
                resp = self.client.step(self.sid, send_idx, action, deadline_mono=self.deadline)
            except DeadlineExceeded as exc:
                self.log.write("step_abandoned_deadline", step_index=send_idx, detail=str(exc)[:500])
                return {"ok": False, "text": "The attempt's time limit has passed. The game tool is closed."}
            except BenchError as exc:
                return self._step_failure(exc, send_idx, action)

            t_recv = self.log.rel()
            late = self.deadline is not None and time.monotonic() > self.deadline
            new_idx = resp.get("step_index")
            invalid = bool(resp.get("invalid_action"))
            new_state = resp.get("state")
            expected = self.idx if invalid else send_idx
            if not isinstance(new_state, dict):
                self.log.write("incident", type="step_response_missing_state", step_index=send_idx,
                               response_keys=sorted(resp.keys()))
                return {"ok": False, "text": "The game server returned an incomplete response; the move's outcome is unknown. Use get_state."}
            ev = {"action": action, "step_index_sent": send_idx, "step_index": new_idx,
                  "invalid_action": invalid, "state": new_state, "t_recv": t_recv, "late": late}
            if new_idx != expected:
                self.log.write("incident", type="step_index_contract", expected=expected, got=new_idx)
            self.log.write("step_result", **ev)
            if isinstance(new_idx, int):
                self.idx = new_idx
            self.state = new_state
            if late:
                # Outcome arrived after the deadline: retained as a late event, never scored.
                return {"ok": False, "text": "The attempt's time limit has passed. The game tool is closed."}
            sl = player_slice(new_state)
            extra = {"invalid_action": invalid}
            if invalid:
                extra["note"] = f"{action!r} is not legal — pick one of legal_actions."
            extra.update(self._timing())
            if self.game_done():
                terminal = "completed" if new_state.get("status") == "completed" else "game_over"
                self.closed_reason = terminal
                self.terminal_t = t_recv
                self.log.write("gate_closed", reason=terminal, state=new_state)
            text = format_state(sl, extra)
        if terminal:
            self.on_terminal(terminal)
        return {"ok": True, "text": text, "data": sl}

    def _step_failure(self, exc: BenchError, send_idx: int, action: str) -> dict:
        """Called with self.lock held."""
        self.log.write("incident", type="step_failed", step_index=send_idx, code=exc.code,
                       detail=str(exc)[:1000])
        if exc.code == 409:
            # Index mismatch: try to re-synchronise from the server's own record of the session.
            try:
                body = self.client.get_session(self.sid)
                st = body.get("state") if isinstance(body, dict) else None
                si = body.get("step_index") if isinstance(body, dict) else None
                if isinstance(st, dict) and isinstance(si, int):
                    self.log.write("resync", step_index=si, state=st)
                    self.idx, self.state = si, st
                    extra = {"note": "The outcome of your last move could not be confirmed; the current state was re-read from the server.",
                             **self._timing()}
                    return {"ok": True, "text": format_state(player_slice(st), extra), "data": player_slice(st)}
            except BenchError as exc2:
                self.log.write("incident", type="resync_failed", detail=str(exc2)[:500])
        return {"ok": False, "text": ("The game server did not accept the request (infrastructure error: "
                                      f"{str(exc)[:300]}). The game state is unchanged as far as the controller knows; "
                                      "you may retry.")}
