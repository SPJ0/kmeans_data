"""Trusted DiG-bench Agent API client (stdlib only). Manager-side; never runs inside a player sandbox.

Adapted from discos-research/dig-bench baseline-harness/core/bench.py at commit
d88405fca4b60c1cb337a830a6b0071a498d3a07 (MIT). Differences from the official client:

- every HTTP exchange is reported to a caller-supplied ``log`` callback (trusted event log);
- step retries are bounded by the attempt deadline, not only by a retry count;
- session creation is NEVER retried automatically: an ambiguous create (network error or
  timeout after the request may have reached the server) is surfaced as ``AmbiguousCreate``
  so the caller can record an infrastructure incident instead of silently opening a second
  game instance.

Carries no game-solving logic.
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request

DEFAULT_SERVER = "https://api.digbench.ai"
USER_AGENT = "dig-vanilla-baseline-controller/1.0 (+https://digbench.ai)"
TRANSIENT_HTTP = (408, 429)


class BenchError(RuntimeError):
    """Deterministic failure (non-retryable 4xx) or retries exhausted."""

    def __init__(self, msg: str, *, code: int | None = None, body: str | None = None):
        super().__init__(msg)
        self.code = code
        self.body = body


class AmbiguousCreate(BenchError):
    """POST /sessions failed in a way that may or may not have created a session."""


class DeadlineExceeded(BenchError):
    """A retry loop stopped because the attempt deadline passed."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class DigClient:
    def __init__(self, server: str, token: str, *, timeout: float = 60.0, log=None):
        server = server.rstrip("/").removesuffix("/api/agent")
        self.server = server
        self.base = server + "/api/agent"
        self._token = token
        self.timeout = timeout
        self.log = log or (lambda kind, **kw: None)

    # -- single HTTP exchange ------------------------------------------------------------
    def _once(self, method: str, path: str, payload: dict | None, timeout: float):
        """One HTTP exchange. Returns (http_status, parsed_json). Raises urllib/OSError on transport failure."""
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        with _OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw)

    def _exchange(self, method: str, path: str, payload: dict | None, timeout: float):
        """Wrap _once; classify the outcome. Returns ('ok', body) / ('http', code, body) / ('transport', msg)."""
        t0 = time.monotonic()
        try:
            status, body = self._once(method, path, payload, timeout)
            self.log("http", method=method, path=path, request=payload, outcome="ok",
                     http_status=status, latency_s=round(time.monotonic() - t0, 3))
            return ("ok", body)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")[:2000]
            self.log("http", method=method, path=path, request=payload, outcome="http_error",
                     http_status=exc.code, body=text, latency_s=round(time.monotonic() - t0, 3))
            return ("http", exc.code, text)
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as exc:
            msg = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
            self.log("http", method=method, path=path, request=payload, outcome="transport_error",
                     error=msg, latency_s=round(time.monotonic() - t0, 3))
            return ("transport", msg)

    # -- endpoints -----------------------------------------------------------------------
    def list_games(self, retries: int = 4):
        last = None
        for k in range(retries):
            r = self._exchange("GET", "/games", None, self.timeout)
            if r[0] == "ok":
                return r[1]
            if r[0] == "http" and r[1] < 500 and r[1] not in TRANSIENT_HTTP:
                raise BenchError(f"GET /games -> HTTP {r[1]}: {r[2]}", code=r[1], body=r[2])
            last = r
            time.sleep(min(2 ** k, 30))
        raise BenchError(f"GET /games failed after {retries} attempts: {last}")

    def create_session(self, game: str, model_name: str, model_version: str) -> dict:
        """Exactly one POST. Never retried here (see module docstring)."""
        r = self._exchange("POST", "/sessions",
                           {"game": game, "model_name": model_name, "model_version": model_version},
                           self.timeout)
        if r[0] == "ok":
            return r[1]
        if r[0] == "http" and r[1] < 500 and r[1] not in TRANSIENT_HTTP:
            # The server answered with a deterministic rejection: no session was created.
            raise BenchError(f"POST /sessions -> HTTP {r[1]}: {r[2]}", code=r[1], body=r[2])
        raise AmbiguousCreate(f"POST /sessions outcome unknown: {r}")

    def get_session(self, sid: str):
        """Read-only re-read of a session (route taken from the report's get_session tool;
        verified against the live server during the smoke test). Returns body or raises."""
        r = self._exchange("GET", f"/sessions/{sid}", None, self.timeout)
        if r[0] == "ok":
            return r[1]
        raise BenchError(f"GET /sessions/{sid} failed: {r}", code=r[1] if r[0] == "http" else None)

    def step(self, sid: str, step_index: int, action: str, *, deadline_mono: float | None = None,
             max_attempts: int = 10) -> dict:
        """Idempotent step: the SAME step_index is resent on transient failure, so a lost response
        cannot apply the action twice (the server returns the cached response for an applied index).
        Backoff is bounded by the attempt deadline. 409 (index mismatch) and other 4xx raise."""
        last = None
        for k in range(max_attempts):
            timeout = self.timeout
            if deadline_mono is not None:
                remaining = deadline_mono - time.monotonic()
                if remaining <= 0:
                    raise DeadlineExceeded(f"deadline passed before step attempt {k + 1}; last={last}")
                timeout = max(1.0, min(timeout, remaining + 30.0))  # allow a late response to land
            r = self._exchange("POST", f"/sessions/{sid}/step",
                               {"step_index": step_index, "action": action}, timeout)
            if r[0] == "ok":
                if k:
                    self.log("step_retry_recovered", step_index=step_index, attempts=k + 1)
                return r[1]
            if r[0] == "http" and r[1] < 500 and r[1] not in TRANSIENT_HTTP:
                raise BenchError(f"step {step_index} -> HTTP {r[1]}: {r[2]}", code=r[1], body=r[2])
            last = r
            wait = min(2 ** k, 30)
            if deadline_mono is not None:
                wait = min(wait, max(0.0, deadline_mono - time.monotonic()))
            self.log("step_retry", step_index=step_index, attempt=k + 1, wait_s=wait, last=str(r)[:300])
            time.sleep(wait)
        raise BenchError(f"step {step_index} failed after {max_attempts} attempts: {last}")


def player_slice(state: dict) -> dict:
    """The permitted player view: exactly the official state_for_model() slice
    (baseline-harness/core/bench.py), nothing added."""
    out = {
        "observation": state.get("observation", ""),
        "level": state.get("level"),
        "max_level": state.get("max_level"),
        "lives_left": state.get("lives_left"),
        "steps_remaining": state.get("steps_remaining"),
        "status": state.get("status"),
        "done": state.get("done"),
        "legal_actions": state.get("actions", []),
    }
    if state.get("mode") is not None:
        out["mode"] = state["mode"]
        out["creative_toggle"] = state.get("creative_toggle")
    if state.get("transition") is not None:
        out["transition"] = state["transition"]
    return out
