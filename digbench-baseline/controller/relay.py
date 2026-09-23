#!/usr/bin/env python3
"""Player-side game tool. Runs INSIDE the player sandbox and holds no secrets.

It knows only a unix-socket path and a per-attempt capability string, and it can only ask the
trusted controller to (a) re-read the current permitted state, (b) submit one action, or
(c) record that the player is stopping unresolved. The controller owns the DiG-bench
credential, the session id, step indexing, the clock and all logging.

Two front ends share one code path:
  * MCP stdio server  (``relay.py mcp``)  -> tools make_move / get_state / stop_attempt
  * command line      (``game state`` / ``game move ACTION`` / ``game stop REASON``)
"""

from __future__ import annotations

import json
import os
import socket
import sys

SOCK = os.environ.get("GAME_SOCKET", "")
CAP = os.environ.get("GAME_CAPABILITY", "")

TOOLS = [
    {
        "name": "make_move",
        "description": (
            "Submit your move. `action` must be EXACTLY one of the legal_actions from the latest "
            "game state. Returns the resulting game state and the time remaining in this attempt."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"action": {"type": "string",
                                      "description": "One legal action token (e.g. '1', '2', 'w', '/')."}},
            "required": ["action"],
        },
    },
    {
        "name": "get_state",
        "description": "Re-read the current game state without taking an action.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "stop_attempt",
        "description": (
            "Declare that you are stopping this attempt unresolved while the game is still in "
            "progress. This permanently closes the game for this attempt."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "Brief reason for stopping."}},
            "required": ["reason"],
        },
    },
]


def ask(req: dict, timeout: float = 4000.0) -> dict:
    req = dict(req, cap=CAP)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(SOCK)
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        return json.loads(buf.decode("utf-8"))
    except Exception as exc:  # the controller is gone (deadline) or unreachable
        return {"ok": False, "text": f"Game tool unavailable: {type(exc).__name__}: {exc}"}


def call_tool(name: str, args: dict, via: str) -> dict:
    if name == "make_move":
        action = args.get("action")
        return ask({"op": "move", "action": action, "via": via})
    if name == "get_state":
        return ask({"op": "state", "via": via})
    if name == "stop_attempt":
        return ask({"op": "stop", "reason": str(args.get("reason", ""))[:2000], "via": via})
    return {"ok": False, "text": f"Unknown tool {name!r}."}


# ---------------------------------------------------------------- MCP (JSON-RPC over stdio)
def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def mcp_main() -> None:
    ask({"op": "hello", "via": "mcp"}, timeout=10)  # lets the controller see the harness is up
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid = msg.get("id")
        method = msg.get("method")
        if mid is None:  # notification (e.g. notifications/initialized)
            continue
        if method == "initialize":
            pv = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": pv,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "game", "version": "1.0"},
            }})
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = msg.get("params") or {}
            r = call_tool(p.get("name", ""), p.get("arguments") or {}, "mcp")
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": r.get("text", "")}],
                "isError": not r.get("ok", False),
            }})
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": mid, "result": {}})
        else:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": f"Method not found: {method}"}})


# ---------------------------------------------------------------- CLI
USAGE = """usage:
  game state              re-read the current game state (no action taken)
  game move ACTION        submit exactly one action from the current legal_actions
  game stop REASON...     declare that you are stopping this attempt unresolved
"""


def cli_main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "state" and not rest:
        r = call_tool("get_state", {}, "cli")
    elif cmd == "move" and len(rest) == 1:
        r = call_tool("make_move", {"action": rest[0]}, "cli")
    elif cmd == "stop" and rest:
        r = call_tool("stop_attempt", {"reason": " ".join(rest)}, "cli")
    else:
        sys.stderr.write(USAGE)
        return 2
    sys.stdout.write(r.get("text", "") + "\n")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        mcp_main()
    else:
        sys.exit(cli_main(sys.argv[1:]))
