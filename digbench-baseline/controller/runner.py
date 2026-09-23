"""Run ONE attempt end to end (manager side, trusted).

  prepare server session -> build fresh sandboxed player home -> launch headless Claude Code
  (stream-json) -> dispatch fixed prompt (clock starts) -> neutral continuations under the fixed
  policy -> stop on terminal server state / player stop / deadline -> kill sandbox -> collect.

Usage:
  python3 -m controller.runner --attempt-id M03 --game P-16 --rep 2 --phase measured
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from . import sandbox
from .digclient import DEFAULT_SERVER, AmbiguousCreate, BenchError, DigClient, player_slice
from .gamectl import EventLog, GameController, format_state, utc_now

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(PROJECT, "prompts")
CA_BUNDLE_SRC = "/root/.ccr/ca-bundle.crt"   # public proxy CA certificate (not a secret)

TEST_PLAYER_BIN = None   # set only by tests (phase=synthetic) to a scripted fake player

CONFIG = {
    "config_version": "v1",
    "model": "claude-opus-5-5",
    "effort": "xhigh",
    "permission_mode": "auto",                 # same mode as this environment's ordinary sessions
    "permission_prompts": "none",             # headless: anything that would prompt is denied, never hangs
    "attempt_seconds": 3600.0,
    "player_continuations": 2,
    "infra_continuations": 3,
    "harness_resumes": 2,
    "bookkeeping_grace_s": 120.0,
    "relay_ready_wait_s": 90.0,
    "session_model_name": "claude-code-vanilla-baseline",
    # Tools whose effects leave the attempt sandbox (cloud routines, push notifications to the
    # account owner, messaging other local agents, account-level design sync). Disallowed for
    # isolation, not difficulty; every tool that acts inside the sandbox stays enabled.
    "disallowed_tools": ["RemoteTrigger", "PushNotification", "SendMessage", "ListAgents", "DesignSync"],
    "webfetch_deny": ["WebFetch(domain:digbench.ai)", "WebFetch(domain:api.digbench.ai)",
                      "WebFetch(domain:www.digbench.ai)"],
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def template_hash() -> str:
    h = hashlib.sha256()
    for name in ("player_prompt_v1.txt", "creative_block_v1.txt", "continuation_v1.txt"):
        h.update(name.encode())
        h.update(read(os.path.join(PROMPTS, name)).encode())
    return h.hexdigest()


def render_prompt(game: str, workdir: str, start_wall: str, deadline_wall: str,
                  description: str, state: dict) -> str:
    sl = player_slice(state)
    toggle = sl.get("creative_toggle")
    creative = ""
    if toggle:
        creative = read(os.path.join(PROMPTS, "creative_block_v1.txt")).format(toggle=json.dumps(toggle))
    return read(os.path.join(PROMPTS, "player_prompt_v1.txt")).format(
        creative_block=creative, game=game, workdir=workdir, start_wall=start_wall,
        deadline_wall=deadline_wall, description=description or "(none provided)",
        initial_state=format_state(sl))


def render_continuation(ctl: GameController, deadline_wall: str) -> str:
    rem = ctl.remaining() or 0.0
    return read(os.path.join(PROMPTS, "continuation_v1.txt")).format(
        state_text=format_state(player_slice(ctl.state), {"elapsed_s": round(time.monotonic() - ctl.t0, 1),
                                                          "time_remaining_s": round(rem, 1)}),
        remaining_min=f"{rem / 60:.1f}", deadline_wall=deadline_wall)


def cli_version() -> str:
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:  # pragma: no cover
        return f"unknown ({exc})"


class Player:
    """One headless Claude Code process inside the sandbox, driven over stream-json."""

    def __init__(self, cmd: list[str], stream_path: str, stderr_path: str, events: queue.Queue, log: EventLog):
        self.events = events
        self.log = log
        self._stream = open(stream_path, "a", encoding="utf-8")
        self._stderr = open(stderr_path, "ab")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._stderr, start_new_session=True)
        self._lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            rec = {"wall": utc_now(), "t": self.log.rel(), "line": line}
            with self._lock:
                self._stream.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self._stream.flush()
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            self.events.put(("stdout", obj))
        rc = self.proc.wait()
        self.events.put(("exit", rc))

    def send(self, text: str, kind: str):
        msg = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]},
               "parent_tool_use_id": None}
        self.log.write("dispatch", message_kind=kind, sha256=sha256_text(text), chars=len(text))
        self.proc.stdin.write((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def kill(self):
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)   # unshare --kill-child takes the PID namespace down
        except ProcessLookupError:
            pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        with self._lock:
            self._stream.close()
        self._stderr.close()


def build_home(key: str, run_dir: str, cap: str) -> dict:
    adir = sandbox.attempt_dir(key)
    if os.path.exists(adir):
        raise RuntimeError(f"attempt dir {adir} already exists; refusing to reuse state")
    home = os.path.join(adir, "home")
    tool = os.path.join(home, ".gametool")
    for d in (home, os.path.join(home, "work"), os.path.join(home, "bin"), os.path.join(home, ".claude"), tool):
        os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(adir, 0o700)
    shutil.copy2(os.path.join(PROJECT, "controller", "relay.py"), os.path.join(tool, "relay.py"))
    shutil.copy2(CA_BUNDLE_SRC, os.path.join(tool, "ca-bundle.crt"))
    if TEST_PLAYER_BIN:
        shutil.copy2(TEST_PLAYER_BIN, os.path.join(tool, "fake_player.py"))
    sock = os.path.join(tool, "ctl.sock")
    relay_env = {"GAME_SOCKET": sock, "GAME_CAPABILITY": cap}
    with open(os.path.join(tool, "mcp.json"), "w") as f:
        json.dump({"mcpServers": {"game": {"type": "stdio", "command": "python3",
                                           "args": [os.path.join(tool, "relay.py"), "mcp"],
                                           "env": relay_env}}}, f, indent=2)
    with open(os.path.join(tool, "settings.json"), "w") as f:
        json.dump({"permissions": {"deny": CONFIG["webfetch_deny"]}}, f, indent=2)
    wrapper = os.path.join(home, "bin", "game")
    with open(wrapper, "w") as f:
        f.write("#!/bin/sh\n"
                f"GAME_SOCKET={sock} GAME_CAPABILITY={cap} exec python3 {os.path.join(tool, 'relay.py')} \"$@\"\n")
    os.chmod(wrapper, 0o755)
    return {"adir": adir, "home": home, "work": os.path.join(home, "work"), "tool": tool, "sock": sock}


def claude_argv(paths: dict, session_id: str, resume: bool) -> list[str]:
    argv = ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            "--model", CONFIG["model"], "--effort", CONFIG["effort"],
            "--permission-mode", CONFIG["permission_mode"], "--permission-prompts", CONFIG["permission_prompts"],
            "--mcp-config", os.path.join(paths["tool"], "mcp.json"), "--strict-mcp-config",
            "--settings", os.path.join(paths["tool"], "settings.json"),
            "--disallowedTools", ",".join(CONFIG["disallowed_tools"])]
    argv += ["--resume", session_id] if resume else ["--session-id", session_id]
    if TEST_PLAYER_BIN:   # synthetic harness tests only: a scripted stand-in for the CLI
        argv = ["python3", os.path.join(paths["tool"], "fake_player.py")] + argv[1:]
    return argv


def collect(paths: dict, run_dir: str, redact: list[str]) -> dict:
    out = os.path.join(run_dir, "player_artifacts")
    os.makedirs(out, exist_ok=True)
    copied = {}
    for src, name in ((paths["work"], "work"), (os.path.join(paths["home"], ".claude", "projects"), "claude_projects")):
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(out, name), symlinks=True, dirs_exist_ok=True)
            copied[name] = sum(len(fs) for _, _, fs in os.walk(os.path.join(out, name)))
    # Also list (not copy) anything else the player created in its home.
    listing = []
    for root, dirs, files in os.walk(paths["home"]):
        for fn in files:
            listing.append(os.path.relpath(os.path.join(root, fn), paths["home"]))
    with open(os.path.join(out, "home_listing.txt"), "w") as f:
        f.write("\n".join(sorted(listing)))
    hits = redact_tree(run_dir, [s for s in redact if s])
    return {"copied_file_counts": copied, "redaction_hits": hits}


def redact_tree(root: str, secrets_: list[str]) -> int:
    hits = 0
    for d, _, files in os.walk(root):
        for fn in files:
            p = os.path.join(d, fn)
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            new = data
            for s in secrets_:
                new = new.replace(s.encode(), b"<redacted>")
            if new != data:
                hits += 1
                with open(p, "wb") as f:
                    f.write(new)
    return hits


def run_attempt(a) -> dict:
    run_dir = os.path.abspath(a.run_dir)
    os.makedirs(os.path.join(run_dir, "trusted"), exist_ok=True)
    log = EventLog(os.path.join(run_dir, "trusted", "events.jsonl"))
    token = os.environ.get("DIGBENCH_API_TOKEN", "").strip()
    if not token:
        log.write("incident", type="missing_credential")
        raise SystemExit("DIGBENCH_API_TOKEN not set")
    server = a.server or DEFAULT_SERVER
    if TEST_PLAYER_BIN and a.phase != "synthetic":
        raise SystemExit("a scripted test player may only be used in the synthetic phase")
    client = DigClient(server, token, log=lambda kind, **kw: log.write(kind, **kw))
    events: queue.Queue = queue.Queue()
    ctl = GameController(client, log, attempt_seconds=a.attempt_seconds,
                         on_terminal=lambda r: events.put(("terminal", r)))
    key = f"{a.attempt_id}-{secrets.token_hex(4)}"
    cap = secrets.token_hex(24)
    session_uuid = str(uuid.uuid4())
    meta = {
        "attempt_id": a.attempt_id, "phase": a.phase, "game": a.game, "rep": a.rep,
        "manifest_sha256": a.manifest_sha256, "config": dict(CONFIG, attempt_seconds=a.attempt_seconds),
        "server": server, "synthetic": server.rstrip("/") != DEFAULT_SERVER,
        "claude_cli_version": cli_version(), "template_sha256": template_hash(),
        "claude_session_id": session_uuid, "sandbox_key": key, "host": {
            "nproc": os.cpu_count(), "concurrency_slot": a.slot, "hostname": socket.gethostname()},
        "created_wall": utc_now(),
    }
    log.write("attempt_meta", **meta)

    # 1. Server session before the clock (manager does not look at gameplay).
    try:
        ctl.prepare(a.game, CONFIG["session_model_name"], CONFIG["model"])
    except AmbiguousCreate as exc:
        return finish(meta, run_dir, log, ctl, "infrastructure_session_create_ambiguous", {}, None, [token, cap])
    except BenchError as exc:
        return finish(meta, run_dir, log, ctl, "infrastructure_session_create_failed", {}, None, [token, cap])
    meta.update(session_id=ctl.sid, seed=ctl.start.get("seed"),
                framework_version=ctl.start.get("framework_version"))

    # 2. Fresh player home + controller socket.
    paths = build_home(key, run_dir, cap)
    ctl.serve(paths["sock"], cap)
    env = sandbox.player_env(paths["home"])

    def launch(resume: bool) -> Player:
        cmd = sandbox.sandbox_command(key, env, claude_argv(paths, session_uuid, resume), paths["work"])
        log.write("player_launch", resume=resume, argv=claude_argv(paths, session_uuid, resume),
                  env_keys=sorted(env.keys()))
        return Player(cmd, os.path.join(run_dir, "stream.jsonl"), os.path.join(run_dir, "stderr.log"), events, log)

    player = launch(resume=False)
    ready = ctl.hello.wait(CONFIG["relay_ready_wait_s"])
    log.write("relay_ready", ready=ready)

    # 3. Dispatch: the clock starts when the complete prompt + first permitted state is sent.
    t0, start_wall = ctl.start_clock()
    deadline_wall = (datetime.fromisoformat(start_wall) + timedelta(seconds=a.attempt_seconds)).isoformat(timespec="milliseconds")
    prompt = render_prompt(a.game, paths["work"], start_wall, deadline_wall,
                           ctl.start.get("description", ""), ctl.state)
    with open(os.path.join(run_dir, "prompt.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)
    meta.update(clock_start_wall=start_wall, deadline_wall=deadline_wall, prompt_sha256=sha256_text(prompt))
    player.send(prompt, "initial")

    # 4. Conversation loop under the fixed continuation/incident policy.
    stop_reason = None
    grace_until = None
    counts = {"player_continuations": 0, "infra_continuations": 0, "resumes": 0, "turns": 0}
    tool_count_at_last_continuation = None
    init_models = []

    def tool_requests() -> int:
        return ctl.tool_requests

    while True:
        now = time.monotonic()
        limit = grace_until if grace_until is not None else ctl.deadline
        try:
            kind, payload = events.get(timeout=max(0.05, limit - now))
        except queue.Empty:
            if grace_until is not None and time.monotonic() >= grace_until:
                log.write("grace_expired")
                break
            if time.monotonic() >= ctl.deadline:
                stop_reason = stop_reason or "time_limit"
                break
            continue
        if kind == "terminal":
            if payload == "time_limit":
                if stop_reason is None:
                    stop_reason = "time_limit"
                break
            if stop_reason is None:
                stop_reason = payload
                grace_until = time.monotonic() + CONFIG["bookkeeping_grace_s"]
                log.write("grace_start", reason=payload, grace_s=CONFIG["bookkeeping_grace_s"])
            continue
        if kind == "stdout":
            typ = payload.get("type")
            if typ == "system" and payload.get("subtype") == "init":
                init_models.append(payload.get("model"))
                log.write("harness_init", model=payload.get("model"), tools=payload.get("tools"),
                          mcp_servers=payload.get("mcp_servers"), permission_mode=payload.get("permissionMode"),
                          claude_code_version=payload.get("claude_code_version"),
                          session_id=payload.get("session_id"))
            if typ == "system" and payload.get("subtype") in ("compact_boundary", "status"):
                log.write("harness_event", subtype=payload.get("subtype"), detail=str(payload)[:500])
            if typ != "result":
                continue
            counts["turns"] += 1
            log.write("turn_end", subtype=payload.get("subtype"), is_error=payload.get("is_error"),
                      num_turns=payload.get("num_turns"), duration_ms=payload.get("duration_ms"),
                      model_usage=payload.get("modelUsage"), total_cost_usd=payload.get("total_cost_usd"),
                      result_chars=len(payload.get("result") or ""))
            if stop_reason is not None:
                log.write("player_final_report_received")
                break
            rem = ctl.remaining() or 0.0
            if rem <= 0:
                stop_reason = "time_limit"
                break
            if payload.get("is_error") or payload.get("subtype") != "success":
                if counts["infra_continuations"] < CONFIG["infra_continuations"]:
                    counts["infra_continuations"] += 1
                    log.write("incident", type="harness_error_turn", detail=str(payload.get("result"))[:500])
                    player.send(render_continuation(ctl, deadline_wall), "infra_continuation")
                    continue
                stop_reason = "infrastructure_harness_errors"
                break
            if tool_count_at_last_continuation is not None and tool_requests() == tool_count_at_last_continuation:
                stop_reason = "player_declined_after_continuation"
                break
            if counts["player_continuations"] < CONFIG["player_continuations"]:
                counts["player_continuations"] += 1
                tool_count_at_last_continuation = tool_requests()
                player.send(render_continuation(ctl, deadline_wall), "continuation")
                continue
            stop_reason = "player_ended_turn_after_continuations"
            break
        if kind == "exit":
            log.write("player_exit", returncode=payload)
            if stop_reason is not None:
                break
            if (ctl.remaining() or 0) > 0 and counts["resumes"] < CONFIG["harness_resumes"]:
                counts["resumes"] += 1
                log.write("incident", type="harness_exit_resume", returncode=payload)
                player.kill()                      # reap + close the exited process's handles
                player = launch(resume=True)
                player.send(render_continuation(ctl, deadline_wall), "resume_continuation")
                continue
            stop_reason = "infrastructure_harness_exit"
            break

    ctl.close(stop_reason or "unknown")
    player.kill()
    log.write("player_killed", stop_reason=stop_reason)
    return finish(meta, run_dir, log, ctl, stop_reason, counts, paths, [token, cap], init_models)


def finish(meta, run_dir, log, ctl, stop_reason, counts, paths, redact, init_models=None) -> dict:
    ctl.shutdown()
    arts = collect(paths, run_dir, redact) if paths else {}
    meta.update(stop_reason=stop_reason, counts=counts, finished_wall=utc_now(),
                reported_models_at_init=init_models or [], artifacts=arts,
                terminal_t=ctl.terminal_t, final_state=ctl.state)
    log.write("attempt_end", stop_reason=stop_reason, counts=counts, final_state=ctl.state)
    log.close()
    redact_tree(run_dir, [s for s in redact if s])
    with open(os.path.join(run_dir, "attempt.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    if paths:
        shutil.rmtree(paths["adir"], ignore_errors=True)   # player state never persists across attempts
    return meta


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--attempt-id", required=True)
    p.add_argument("--game", required=True)
    p.add_argument("--rep", type=int, default=0)
    p.add_argument("--phase", choices=["measured", "smoke", "synthetic", "replacement"], required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--server", default=None)
    p.add_argument("--attempt-seconds", type=float, default=CONFIG["attempt_seconds"])
    p.add_argument("--manifest-sha256", default=None)
    p.add_argument("--slot", type=int, default=0)
    a = p.parse_args(argv)
    if os.path.exists(os.path.join(a.run_dir, "trusted", "events.jsonl")):
        raise SystemExit(f"{a.run_dir} already has a trusted log; refusing to overwrite")
    meta = run_attempt(a)
    print(json.dumps({k: meta.get(k) for k in ("attempt_id", "game", "session_id", "stop_reason")}))


if __name__ == "__main__":
    main()
