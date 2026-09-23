"""Player sandbox: fresh per-attempt home, private PID + mount namespaces, capabilities dropped.

The player CLI runs as uid 0 because this cloud container's harness authentication is only readable
by root, and the manager must not copy that credential. Isolation therefore relies on namespaces,
not on file permissions:

* PID namespace (``unshare --pid --fork --kill-child --mount-proc``): the player sees only its own
  processes; killing the namespace's init at the deadline kills every descendant.
* Mount namespace: tmpfs masks over manager/sibling locations (the experiment repo under
  /home/user, /root including the manager's Claude transcripts, /tmp including the manager
  scratchpad, /srv/dig with only this attempt's directory mounted back, and other shared stores).
* ``setpriv --no-new-privs --bounding-set=-all --inh-caps=-all`` before exec: the player process
  tree has no capabilities, so it cannot unmount the masks, change mounts, or alter firewall rules.
* ``env -i``: only an allowlisted environment reaches the player (no DiG-bench credential, no
  manager session variables).
"""

from __future__ import annotations

import os
import shlex

DIG_ROOT = "/srv/dig"
MASKS = ["/home/user", "/home/ubuntu", "/root", "/var/tmp", "/dev/shm", "/mnt/user-data"]
SOCKET_MASKS = ["/var/run/docker.sock", "/run/docker.sock"]


def attempt_dir(attempt_key: str) -> str:
    return os.path.join(DIG_ROOT, attempt_key)


def player_env(home: str, extra: dict | None = None) -> dict:
    """Allowlisted environment for the player process tree."""
    env = {
        "HOME": home,
        "PATH": f"{home}/bin:/opt/node22/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "dumb",
        "SHELL": "/bin/bash",
        "TMPDIR": "/tmp",
        "USER": "root",
        "CLAUDE_CONFIG_DIR": f"{home}/.claude",
        "DISABLE_AUTOUPDATER": "1",     # keep the harness version fixed for the whole study
        "SSL_CERT_FILE": f"{home}/.gametool/ca-bundle.crt",
        "NODE_EXTRA_CA_CERTS": f"{home}/.gametool/ca-bundle.crt",
        "REQUESTS_CA_BUNDLE": f"{home}/.gametool/ca-bundle.crt",
        "PIP_CERT": f"{home}/.gametool/ca-bundle.crt",
    }
    # Ordinary outbound networking of this container (same egress policy as any session here).
    for k in ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    env.update(extra or {})
    return env


def sandbox_command(attempt_key: str, env: dict, argv: list[str], cwd: str) -> list[str]:
    adir = attempt_dir(attempt_key)
    q = shlex.quote
    lines = [
        "set -e",
        "mount -t tmpfs -o mode=1777 tmpfs /tmp",
        "mkdir /tmp/.stage",
        f"mount --bind {q(adir)} /tmp/.stage",
        f"mount -t tmpfs -o mode=755 tmpfs {DIG_ROOT}",
        f"mkdir -p {q(adir)}",
        f"mount --move /tmp/.stage {q(adir)}",
        "rmdir /tmp/.stage",
    ]
    for d in MASKS:
        lines.append(f"if [ -d {d} ]; then mount -t tmpfs -o mode=755 tmpfs {d}; fi")
    for s in SOCKET_MASKS:
        lines.append(f"if [ -S {s} ]; then mount --bind /dev/null {s}; fi")
    env_args = " ".join(q(f"{k}={v}") for k, v in env.items())
    cmd = " ".join(q(a) for a in argv)
    lines.append(f"cd {q(cwd)}")
    lines.append("exec setpriv --no-new-privs --bounding-set=-all --inh-caps=-all "
                 f"env -i {env_args} {cmd}")
    script = "\n".join(lines)
    return ["unshare", "--pid", "--fork", "--kill-child", "--mount-proc", "--mount",
            "--propagation", "private", "--", "/bin/sh", "-c", script]
