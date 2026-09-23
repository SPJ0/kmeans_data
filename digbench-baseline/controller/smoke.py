"""Excluded P-1 smoke test + live API contract audit (manager side).

1. GET /games: verify the measured game ids exist (and record any tier metadata returned).
2. One sandboxed player attempt on P-1 with a 10-minute clock (phase=smoke, never scored).
3. After the attempt has fully stopped, audit the live protocol on the SMOKE session only:
   GET /sessions/{id}; resend the last applied step_index (must return the cached response, not
   apply twice); a stale step_index (expect 409). Results -> runs/smoke/<id>/api_audit.json.

  python3 -m controller.smoke [--seconds 600]
"""

from __future__ import annotations

import argparse
import json
import os
import time

from . import runner
from .digclient import DEFAULT_SERVER, BenchError, DigClient

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=600.0)
    ap.add_argument("--game", default="P-1")
    ap.add_argument("--check-games", nargs="*", default=["P-1", "P-16", "P-19"])
    a = ap.parse_args(argv)
    token = os.environ.get("DIGBENCH_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("DIGBENCH_API_TOKEN not set")
    label = f"SMOKE-{a.game}-{time.strftime('%Y%m%dT%H%M%S')}"
    run_dir = os.path.join(PROJECT, "runs", "smoke", label)
    os.makedirs(run_dir, exist_ok=True)
    audit = {"label": label}
    alog = []
    client = DigClient(DEFAULT_SERVER, token, log=lambda kind, **kw: alog.append(dict(kw, kind=kind)))

    games = client.list_games()
    audit["games_response"] = games
    names = games.get("games", []) if isinstance(games, dict) else games
    flat = [g if isinstance(g, str) else (g.get("name") or g.get("id") or g.get("game")) for g in names]
    audit["games_present"] = {g: (g in flat) for g in a.check_games}
    with open(os.path.join(run_dir, "api_audit.json"), "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
    missing = [g for g, ok in audit["games_present"].items() if not ok]
    if missing:
        raise SystemExit(f"games not listed by the live server: {missing} (see api_audit.json)")

    ns = argparse.Namespace(attempt_id=label, game=a.game, rep=0, phase="smoke", run_dir=run_dir,
                            server=None, attempt_seconds=a.seconds, manifest_sha256=None, slot=0)
    meta = runner.run_attempt(ns)
    audit["attempt"] = {k: meta.get(k) for k in ("session_id", "seed", "framework_version", "stop_reason",
                                                 "counts", "reported_models_at_init", "clock_start_wall")}

    # ---- live contract audit on the (finished, excluded) smoke session
    sid = meta.get("session_id")
    evs = [json.loads(l) for l in open(os.path.join(run_dir, "trusted", "events.jsonl"))]
    applied = [e for e in evs if e["kind"] == "step_result" and not e.get("invalid_action")]
    try:
        body = client.get_session(sid)
        audit["get_session"] = {"ok": True, "keys": sorted(body.keys()) if isinstance(body, dict) else None,
                                "step_index": body.get("step_index") if isinstance(body, dict) else None}
    except BenchError as exc:
        audit["get_session"] = {"ok": False, "error": str(exc)[:500]}
    if applied:
        last = applied[-1]
        try:
            again = client.step(sid, last["step_index"], last["action"], max_attempts=2)
            audit["idempotent_replay"] = {
                "resent_index": last["step_index"], "returned_index": again.get("step_index"),
                "state_identical": again.get("state") == last["state"]}
        except BenchError as exc:
            audit["idempotent_replay"] = {"error": str(exc)[:500], "code": exc.code}
        if last["step_index"] >= 2:
            try:
                r = client.step(sid, last["step_index"] - 1, last["action"], max_attempts=1)
                audit["stale_index"] = {"http": 200, "returned_index": r.get("step_index")}
            except BenchError as exc:
                audit["stale_index"] = {"code": exc.code, "error": str(exc)[:300]}
    audit["http_log"] = alog
    with open(os.path.join(run_dir, "api_audit.json"), "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in audit.items() if k != "http_log"}, indent=2, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
