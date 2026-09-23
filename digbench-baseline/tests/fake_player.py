"""Scripted stand-in for the Claude Code CLI (stream-json), used ONLY by synthetic runner-policy
tests. MODE is substituted by the test before the file is copied into the sandbox."""

import json
import os
import signal
import subprocess
import sys
import time

MODE = "__MODE__"
HERE = os.path.dirname(os.path.abspath(__file__))


def out(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def relay_hello():
    cfg = json.load(open(os.path.join(HERE, "mcp.json")))["mcpServers"]["game"]["env"]
    os.environ.update(cfg)
    sys.path.insert(0, HERE)
    import relay  # noqa: E402
    relay.SOCK, relay.CAP = cfg["GAME_SOCKET"], cfg["GAME_CAPABILITY"]
    relay.ask({"op": "hello", "via": "fake"}, timeout=10)


def game(*args):
    return subprocess.run(["game", *args], capture_output=True, text=True).stdout


def result(text):
    out({"type": "result", "subtype": "success", "is_error": False, "num_turns": 1, "duration_ms": 1,
         "result": text})


def main():
    resumed = "--resume" in sys.argv
    relay_hello()
    out({"type": "system", "subtype": "init", "model": "fake-player", "tools": [], "mcp_servers": [],
         "permissionMode": "n/a", "claude_code_version": "fake", "session_id": "fake"})
    for line in sys.stdin:
        if not line.strip():
            continue
        if MODE == "idle":
            result("I will not act.")
        elif MODE == "act_each_turn" or (MODE == "crash_once" and resumed):
            game("move", "r")
            result("moved once")
        elif MODE == "crash_once":
            game("move", "r")
            sys.exit(3)
        elif MODE == "hang":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            subprocess.Popen(["sh", "-c", "while true; do date +%s.%N >> heartbeat.txt; sleep 0.2; done"],
                             start_new_session=True)
            while True:
                game("move", "l")
                time.sleep(0.5)


if __name__ == "__main__":
    main()
