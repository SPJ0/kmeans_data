"""Run the frozen manifest: at most N concurrent attempts, in manifest order, each as its own
runner subprocess. Resumable: attempts that already have a trusted log are never re-run (an
interrupted one is reported, and only the incident policy can authorize a linked replacement).

  nohup python3 -m controller.schedule --manifest manifest.json > runs/measured/scheduler.out 2>&1 &
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(PROJECT, "manifest.json"))
    ap.add_argument("--only", nargs="*", help="restrict to these attempt ids (e.g. an authorized replacement)")
    a = ap.parse_args(argv)
    manifest = json.load(open(a.manifest))
    msha = sha256_file(a.manifest)
    # The protocol and every file that shapes player experience must match the frozen hashes.
    for rel, h in manifest["frozen_files_sha256"].items():
        got = sha256_file(os.path.join(PROJECT, rel))
        if got != h:
            sys.exit(f"frozen file changed: {rel} ({got} != {h}); create a new protocol version instead")
    conc = int(manifest["max_concurrent"])
    items = [x for x in manifest["attempts"] + manifest.get("replacements", [])
             if not a.only or x["id"] in a.only]
    items.sort(key=lambda x: x["order"])
    slots = threading.Semaphore(conc)
    slot_ids = list(range(conc))
    slot_lock = threading.Lock()
    logf = open(os.path.join(PROJECT, "runs", manifest["phase_dir"], "scheduler.log"), "a")

    def log(msg):
        logf.write(f"{now()} {msg}\n")
        logf.flush()

    log(f"scheduler start manifest={msha} items={[x['id'] for x in items]} concurrency={conc}")

    def run(item, slot):
        rd = os.path.join(PROJECT, "runs", item.get("phase_dir", manifest["phase_dir"]), item["id"])
        cmd = [sys.executable, "-m", "controller.runner", "--attempt-id", item["id"], "--game", item["game"],
               "--rep", str(item.get("rep", 0)), "--phase", item.get("phase", "measured"), "--run-dir", rd,
               "--manifest-sha256", msha, "--slot", str(slot)]
        log(f"launch {item['id']} game={item['game']} rep={item.get('rep')} slot={slot}")
        os.makedirs(rd, exist_ok=True)
        with open(os.path.join(rd, "runner.out"), "a") as out:
            rc = subprocess.run(cmd, cwd=PROJECT, stdout=out, stderr=subprocess.STDOUT).returncode
        log(f"done {item['id']} rc={rc}")

    threads = []
    for item in items:
        rd = os.path.join(PROJECT, "runs", item.get("phase_dir", manifest["phase_dir"]), item["id"])
        if os.path.exists(os.path.join(rd, "trusted", "events.jsonl")):
            done = os.path.exists(os.path.join(rd, "attempt.json"))
            log(f"skip {item['id']} (already {'finished' if done else 'STARTED BUT UNFINISHED - see incident policy'})")
            continue
        slots.acquire()
        with slot_lock:
            slot = slot_ids.pop(0)

        def worker(item=item, slot=slot):
            try:
                run(item, slot)
            finally:
                with slot_lock:
                    slot_ids.append(slot)
                slots.release()

        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
        time.sleep(5)   # stagger launches slightly so session creation is not simultaneous
    for t in threads:
        t.join()
    log("scheduler end")


if __name__ == "__main__":
    main()
