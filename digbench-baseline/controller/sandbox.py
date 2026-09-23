"""Player sandbox: fresh per-attempt home, private PID + mount namespaces, capabilities dropped.

The player CLI runs as uid 0 because this cloud container's harness authentication is only readable
by root, and the manager must not copy that credential. Isolation therefore relies on namespaces,
not on file permissions:

* PID namespace (``unshare --pid --fork --kill-child --mount-proc``): the player sees only its own
  processes; killing the namespace's init at the deadline kills every descendant.
* Mount namespace: tmpfs masks over manager/sibling locations (the experiment repo under
  /home/user, /root including the manager's Claude transcripts, /tmp including the manager
  scratchpad, /home/claude except the harness's own credential file, /srv/dig with only this
  attempt's directory mounted back, and other shared stores); a minimal /dev with no block
  devices (so the raw disk cannot be read around the masks); read-only root filesystem, /sys and
  /proc/sys; private IPC and UTS namespaces.
* ``setpriv --no-new-privs --bounding-set=-all --inh-caps=-all`` before exec: the player process
  tree has no capabilities, so it cannot unmount the masks, change mounts, or alter firewall rules.
* Network namespace: no route anywhere. A capability-less bridge inside the namespace forwards
  127.0.0.1:3128 to the manager's egress filter (controller/netfilter.py), which is therefore the
  player's only egress and logs every destination.
* ``env -i``: only an allowlisted environment reaches the player (no DiG-bench credential, no
  manager session variables).
"""

from __future__ import annotations

import os
import shlex

DIG_ROOT = "/srv/dig"
# Hidden behind empty tmpfs. /home/claude holds the container's session-ingress token, launcher
# settings and hooks; only the harness's own model credential file is mounted back (read-only),
# because the CLI authenticates with it, as any ordinary Claude Code install reads its own login.
MASKS = ["/home/user", "/home/ubuntu", "/home/claude", "/root", "/var/tmp", "/mnt/user-data"]
HARNESS_CREDENTIAL = "/home/claude/.claude/remote/.oauth_token"
SOCKET_MASKS = ["/var/run/docker.sock", "/run/docker.sock"]
BRIDGE_PORT = 3128
DROP = "setpriv --no-new-privs --bounding-set=-all --inh-caps=-all"
# Minimal /dev (no block devices: uid 0 could otherwise read the raw disk under every mask).
DEV_NODES = [("null", 1, 3), ("zero", 1, 5), ("full", 1, 7), ("random", 1, 8), ("urandom", 1, 9),
             ("tty", 5, 0)]


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
    # All egress goes through the in-namespace bridge to the manager's filter.
    proxy = f"http://127.0.0.1:{BRIDGE_PORT}"
    env.update({"HTTPS_PROXY": proxy, "https_proxy": proxy, "NO_PROXY": "localhost,127.0.0.1,::1",
                "no_proxy": "localhost,127.0.0.1,::1"})
    env.update(extra or {})
    return env


def sandbox_command(attempt_key: str, env: dict, argv: list[str], cwd: str, tool_dir: str) -> list[str]:
    adir = attempt_dir(attempt_key)
    bridge = os.path.join(tool_dir, "netbridge.py")
    netsock = os.path.join(tool_dir, "net.sock")
    q = shlex.quote
    cred = HARNESS_CREDENTIAL
    lines = [
        "set -e",
        # private /tmp first: it doubles as the staging area for the mounts moved back below
        "mount -t tmpfs -o mode=1777 tmpfs /tmp",
        "mkdir /tmp/.stage",
        f"mount --bind {q(adir)} /tmp/.stage",
        f"if [ -f {cred} ]; then touch /tmp/.cred && mount --bind {cred} /tmp/.cred; fi",
        # minimal /dev
        "mount -t tmpfs -o mode=755,nosuid tmpfs /dev",
    ]
    for name, major, minor in DEV_NODES:
        lines.append(f"mknod -m 666 /dev/{name} c {major} {minor}")
    lines += [
        "mkdir -p /dev/pts /dev/shm",
        "mount -t devpts -o newinstance,ptmxmode=0666,mode=620 devpts /dev/pts",
        "ln -s pts/ptmx /dev/ptmx",
        "mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs /dev/shm",
        "ln -s /proc/self/fd /dev/fd && ln -s /proc/self/fd/0 /dev/stdin && "
        "ln -s /proc/self/fd/1 /dev/stdout && ln -s /proc/self/fd/2 /dev/stderr",
        # kernel interfaces read-only / hidden
        "mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys",
        "mount --bind /proc/sys /proc/sys && mount -o remount,bind,ro /proc/sys",
        "if [ -e /proc/sysrq-trigger ]; then mount --bind /dev/null /proc/sysrq-trigger; fi",
        # only this attempt's directory under /srv/dig
        f"mount -t tmpfs -o mode=755 tmpfs {DIG_ROOT}",
        f"mkdir -p {q(adir)}",
        f"mount --move /tmp/.stage {q(adir)}",
        "rmdir /tmp/.stage",
    ]
    for d in MASKS:
        lines.append(f"if [ -d {d} ]; then mount -t tmpfs -o mode=755 tmpfs {d}; fi")
    lines += [
        f"if [ -f /tmp/.cred ]; then mkdir -p {q(os.path.dirname(cred))} && touch {cred} && "
        f"mount --move /tmp/.cred {cred} && mount -o remount,bind,ro {cred} && rm -f /tmp/.cred; fi",
    ]
    for s_ in SOCKET_MASKS:
        lines.append(f"if [ -S {s_} ]; then mount --bind /dev/null {s_}; fi")
    # Root filesystem read-only in this namespace: no player can leave files for a later attempt.
    # Writable: the attempt directory, /tmp, /var/tmp, /dev/shm and the masked (ephemeral) dirs.
    lines.append("mount -o remount,bind,ro /")
    lines.append(f"python3 {q(bridge)} lo-up")
    lines.append(f"{DROP} python3 {q(bridge)} {BRIDGE_PORT} {q(netsock)} </dev/null >/dev/null 2>&1 &")
    lines.append("i=0; while [ $i -lt 50 ]; do python3 -c 'import socket; socket.socket().connect((\"127.0.0.1\", "
                 f"{BRIDGE_PORT}))' 2>/dev/null && break; i=$((i+1)); sleep 0.1; done")
    env_args = " ".join(q(f"{k}={v}") for k, v in env.items())
    cmd = " ".join(q(a) for a in argv)
    lines.append(f"cd {q(cwd)}")
    lines.append(f"exec {DROP} env -i {env_args} {cmd}")
    script = "\n".join(lines)
    return ["unshare", "--pid", "--fork", "--kill-child", "--mount-proc", "--mount", "--net", "--ipc", "--uts",
            "--propagation", "private", "--", "/bin/sh", "-c", script]
