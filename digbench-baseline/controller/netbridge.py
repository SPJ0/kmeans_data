"""Runs INSIDE the player's network namespace, without capabilities or secrets. Listens on
127.0.0.1:PORT and forwards each TCP connection to the manager's egress-filter unix socket, which
is the namespace's only way out."""

import select
import socket
import sys
import threading


def splice(a, b):
    socks = [a, b]
    try:
        while True:
            r, _, _ = select.select(socks, [], [], 900)
            if not r:
                return
            for s in r:
                data = s.recv(65536)
                if not data:
                    return
                (b if s is a else a).sendall(data)
    except OSError:
        return
    finally:
        a.close()
        b.close()


def handle(c, path):
    try:
        u = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        u.connect(path)
    except OSError:
        c.close()
        return
    splice(c, u)


def loopback_up():
    """Bring up `lo` in a fresh network namespace (no `ip` binary in this image)."""
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fcntl.ioctl(s.fileno(), 0x8914, struct.pack("16sH14s", b"lo", 0x1 | 0x8 | 0x40, b"\0" * 14))  # SIOCSIFFLAGS


def main():
    if sys.argv[1] == "lo-up":
        loopback_up()
        return
    port, path = int(sys.argv[1]), sys.argv[2]
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(128)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c, path), daemon=True).start()


if __name__ == "__main__":
    main()
