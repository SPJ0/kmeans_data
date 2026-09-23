"""Manager-side egress filter for one player (trusted; runs outside the sandbox).

The player's network namespace has no route anywhere. Its only egress is 127.0.0.1:3128 inside
the namespace, which netbridge.py forwards to this filter's unix socket. The filter accepts HTTP
CONNECT only, refuses the benchmark's own hosts (so players cannot browse benchmark pages or reach
the game API with another session) and IP-literal targets (which would sidestep name matching),
and otherwise forwards exactly as this container's ordinary
networking would: hosts on NO_PROXY directly, everything else through the container's egress
proxy. Every destination is logged to the attempt's trusted log.
"""

from __future__ import annotations

import ipaddress
import os
import select
import socket
import threading
from urllib.parse import urlparse

DENY_SUFFIXES = ("digbench.ai",)


def _split_no_proxy(v: str) -> list[str]:
    return [x.strip().lstrip("*").lower() for x in v.split(",") if x.strip()]


def _host_matches(host: str, patterns: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for p in patterns:
        if not p or "/" in p:          # CIDR entries: only literal loopback-style IPs matter here
            continue
        p = p.rstrip(".")
        if host == p.lstrip(".") or (p.startswith(".") and host.endswith(p)) or host.endswith("." + p):
            return True
    return False


def is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def denied(host: str) -> bool:
    """Benchmark hosts by name, and any IP-literal target (which would sidestep name matching)."""
    return is_ip_literal(host) or _host_matches(host, list(DENY_SUFFIXES))


class EgressFilter:
    def __init__(self, sock_path: str, log, upstream: str | None = None, no_proxy: str | None = None):
        self.sock_path = sock_path
        self.log = log
        up = upstream if upstream is not None else (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "")
        u = urlparse(up) if up else None
        self.upstream = (u.hostname, u.port or 80) if u and u.hostname else None
        self.no_proxy = _split_no_proxy(no_proxy if no_proxy is not None else
                                        (os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""))
        self._srv = None

    def start(self):
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(self.sock_path)
        os.chmod(self.sock_path, 0o600)
        srv.listen(64)
        self._srv = srv
        threading.Thread(target=self._accept, daemon=True).start()
        return self

    def stop(self):
        if self._srv:
            try:
                self._srv.close()
            except OSError:
                pass

    def _accept(self):
        while True:
            try:
                c, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(c,), daemon=True).start()

    def _handle(self, c: socket.socket):
        up = None
        try:
            c.settimeout(30)
            head = b""
            while b"\r\n\r\n" not in head and len(head) < 65536:
                chunk = c.recv(4096)
                if not chunk:
                    return
                head += chunk
            first = head.split(b"\r\n", 1)[0].decode("latin-1")
            parts = first.split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                self.log("egress", method=parts[0] if parts else "?", target=parts[1][:200] if len(parts) > 1 else "",
                         decision="rejected_non_connect")
                c.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
                return
            target = parts[1]
            host, _, port = target.rpartition(":")
            host = host.strip("[]")
            port = int(port) if port.isdigit() else 443
            if denied(host):
                self.log("egress", host=host, port=port,
                         decision="denied_ip_literal" if is_ip_literal(host) else "denied_benchmark_host")
                c.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                return
            route = "direct" if (self.upstream is None or _host_matches(host, self.no_proxy)) else "upstream"
            if route == "direct":
                up = socket.create_connection((host, port), timeout=30)
            else:
                up = socket.create_connection(self.upstream, timeout=30)
                up.sendall(f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n".encode())
                resp = b""
                while b"\r\n\r\n" not in resp and len(resp) < 65536:
                    chunk = up.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                status = resp.split(b"\r\n", 1)[0].decode("latin-1", "replace")
                if " 200" not in status:
                    self.log("egress", host=host, port=port, decision="upstream_refused", status=status[:100])
                    c.sendall(resp or b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                    return
            self.log("egress", host=host, port=port, decision="allowed", route=route)
            c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            c.settimeout(None)
            up.settimeout(None)
            splice(c, up)
        except OSError as exc:
            try:
                self.log("egress", decision="error", error=str(exc)[:200])
                c.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
        finally:
            for s in (c, up):
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass


def splice(a: socket.socket, b: socket.socket, idle_timeout: float = 900.0):
    socks = [a, b]
    while True:
        r, _, x = select.select(socks, [], socks, idle_timeout)
        if x or not r:
            return
        for s in r:
            try:
                data = s.recv(65536)
            except OSError:
                return
            if not data:
                return
            (b if s is a else a).sendall(data)
