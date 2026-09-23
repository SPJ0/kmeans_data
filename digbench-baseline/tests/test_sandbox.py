"""Isolation probes for the player sandbox (needs root; no model involved).

Harmless marker files are planted in manager, scratch, sibling and shared locations; a shell
running inside the sandbox must find none of them, must have no capabilities, must see only its
own processes, must not be able to undo the mount masks, and must reach the network only through
the manager's egress filter (benchmark hosts refused, every destination logged).

  cd digbench-baseline && python3 -m unittest tests.test_sandbox -v
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

from controller import sandbox  # noqa: E402
from controller.netfilter import EgressFilter, denied  # noqa: E402

MARK = "ISOLATION-MARKER-" + secrets.token_hex(4)
PLANT = [
    os.path.join(PROJECT, "runs", ".probe_marker"),               # manager experiment tree
    "/root/.probe_marker",                                        # manager home / Claude transcripts
    "/tmp/.probe_marker",                                         # shared tmp (manager scratchpad lives here)
    "/var/tmp/.probe_marker",
    "/mnt/user-data/working/.probe_marker",
    os.path.join(sandbox.DIG_ROOT, "probe-sibling", "marker"),    # a sibling attempt's directory
    "/home/claude/.probe_marker",                                 # container session files
    "/home/claude/.claude/remote/.probe_marker",
]


class SandboxIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = "probe-" + secrets.token_hex(3)
        cls.adir = sandbox.attempt_dir(cls.key)
        cls.home = os.path.join(cls.adir, "home")
        cls.tool = os.path.join(cls.home, ".gametool")
        os.makedirs(cls.tool)
        shutil.copy2(os.path.join(PROJECT, "controller", "netbridge.py"), cls.tool)
        shutil.copy2("/root/.ccr/ca-bundle.crt", os.path.join(cls.tool, "ca-bundle.crt"))
        for p in PLANT:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(MARK + "\n")
        cls.events = []
        cls.filter = EgressFilter(os.path.join(cls.tool, "net.sock"),
                                  lambda kind, **kw: cls.events.append(dict(kw, kind=kind))).start()
        probe = f"""
echo "caps=$(grep CapEff /proc/self/status | awk '{{print $2}}')"
echo "nprocs=$(ls /proc | grep -c '^[0-9]')"
echo "srv=$(ls {sandbox.DIG_ROOT} | tr '\\n' ' ')"
echo "hits=$(grep -rls {MARK} / --exclude-dir=proc --exclude-dir=sys 2>/dev/null | wc -l)"
umount /root >/dev/null 2>&1 && echo umount=yes || echo umount=no
python3 -c 'import socket; socket.create_connection(("127.0.0.1", 42017), 3)' >/dev/null 2>&1 && echo upstream_direct=yes || echo upstream_direct=no
python3 -c 'import socket; socket.create_connection(("pypi.org", 443), 5)' >/dev/null 2>&1 && echo raw_egress=yes || echo raw_egress=no
echo "pypi=$(curl -sS -m 20 -o /dev/null -w '%{{http_code}}' https://pypi.org/simple/pip/ 2>/dev/null)"
echo "bench=$(curl -sS -m 20 -o /dev/null -w '%{{http_code}}' https://digbench.ai/ 2>&1 | tail -c 60)"
echo "blockdevs=$(find /dev -type b 2>/dev/null | wc -l)"
head -c 16 /dev/vda >/dev/null 2>&1 && echo rawdisk=yes || echo rawdisk=no
touch /etc/.probe_write >/dev/null 2>&1 && echo rootfs_writable=yes || echo rootfs_writable=no
touch /opt/.probe_write >/dev/null 2>&1 && echo opt_writable=yes || echo opt_writable=no
touch {cls.home}/.probe_write >/dev/null 2>&1 && echo home_writable=yes || echo home_writable=no
touch /tmp/.probe_write >/dev/null 2>&1 && echo tmp_writable=yes || echo tmp_writable=no
echo 1 > /proc/sys/kernel/printk_ratelimit 2>/dev/null && echo procsys_writable=yes || echo procsys_writable=no
[ -e /home/claude/.claude/remote/.session_ingress_token ] && echo ingress_visible=yes || echo ingress_visible=no
[ -e /home/claude/.claude/launcher-settings.json ] && echo launcher_visible=yes || echo launcher_visible=no
[ -f {sandbox.HARNESS_CREDENTIAL} ] && echo harness_cred_present=yes || echo harness_cred_present=no
echo x >> {sandbox.HARNESS_CREDENTIAL} 2>/dev/null && echo harness_cred_writable=yes || echo harness_cred_writable=no
echo "iplit=$(curl -sS -m 20 -o /dev/null -w '%{{http_code}}' https://1.1.1.1/ 2>&1 | tail -c 60)"
echo "benchapi=$(curl -sS -m 20 -o /dev/null -w '%{{http_code}}' https://api.digbench.ai/api/agent/games 2>&1 | tail -c 60)"
"""
        env = sandbox.player_env(cls.home)
        cmd = sandbox.sandbox_command(cls.key, env, ["/bin/bash", "-c", probe], cls.home, cls.tool)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        cls.out = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
        cls.stderr = r.stderr

    @classmethod
    def tearDownClass(cls):
        cls.filter.stop()
        for p in PLANT:
            try:
                os.remove(p)
            except OSError:
                pass
        shutil.rmtree(os.path.join(sandbox.DIG_ROOT, "probe-sibling"), ignore_errors=True)
        shutil.rmtree(cls.adir, ignore_errors=True)

    def test_no_capabilities_and_private_pid_view(self):
        self.assertEqual(self.out.get("caps"), "0000000000000000", self.stderr)
        self.assertLessEqual(int(self.out.get("nprocs", "999")), 8)
        self.assertEqual(self.out.get("umount"), "no")

    def test_no_marker_visible(self):
        self.assertEqual(self.out.get("hits"), "0")
        self.assertEqual(self.out.get("srv", "").split(), [self.key])

    def test_no_raw_disk_and_readonly_root(self):
        self.assertEqual(self.out.get("blockdevs"), "0", self.stderr)
        self.assertEqual(self.out.get("rawdisk"), "no")
        self.assertEqual(self.out.get("rootfs_writable"), "no")
        self.assertEqual(self.out.get("opt_writable"), "no")
        self.assertEqual(self.out.get("procsys_writable"), "no")
        self.assertEqual(self.out.get("home_writable"), "yes")
        self.assertEqual(self.out.get("tmp_writable"), "yes")
        self.assertFalse(os.path.exists("/etc/.probe_write"))

    def test_container_session_files_hidden(self):
        self.assertEqual(self.out.get("ingress_visible"), "no")
        self.assertEqual(self.out.get("launcher_visible"), "no")
        self.assertEqual(self.out.get("harness_cred_present"), "yes")    # the CLI's own login only
        self.assertEqual(self.out.get("harness_cred_writable"), "no")

    def test_network_only_through_filter(self):
        self.assertEqual(self.out.get("upstream_direct"), "no")
        self.assertEqual(self.out.get("raw_egress"), "no")
        self.assertEqual(self.out.get("pypi"), "200")
        self.assertNotEqual(self.out.get("bench"), "200")
        self.assertNotEqual(self.out.get("benchapi"), "200")
        hosts = {(e.get("host"), e.get("decision")) for e in self.events if e["kind"] == "egress"}
        self.assertIn(("pypi.org", "allowed"), hosts)
        self.assertIn(("digbench.ai", "denied_benchmark_host"), hosts)
        self.assertIn(("api.digbench.ai", "denied_benchmark_host"), hosts)
        self.assertNotEqual(self.out.get("iplit"), "200")
        self.assertIn(("1.1.1.1", "denied_ip_literal"), hosts)

    def test_deny_matching(self):
        self.assertTrue(denied("digbench.ai"))
        self.assertTrue(denied("API.DigBench.ai"))
        self.assertTrue(denied("www.digbench.ai."))
        self.assertFalse(denied("notdigbench.ai"))
        self.assertFalse(denied("pypi.org"))
        self.assertTrue(denied("1.2.3.4"))
        self.assertTrue(denied("[2606:4700::1111]"))


if __name__ == "__main__":
    unittest.main()
