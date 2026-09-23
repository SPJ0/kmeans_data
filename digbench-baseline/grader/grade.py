"""Automatic grader. Reads ONLY trusted controller logs (runs/<phase>/<attempt>/trusted/events.jsonl
and attempt.json) plus the frozen manifest; player prose never affects a score.

  python3 -m grader.grade --manifest manifest.json --runs runs --out reports/generated

Outputs results.json (per-attempt derived records + integrity checks) and tables.md.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict

OFFICIAL_SERVER = "https://api.digbench.ai"
CHECKPOINTS = (900, 1800, 3600)
INFRA_STOPS = {
    "infrastructure_session_create_ambiguous", "infrastructure_session_create_failed",
    "infrastructure_harness_exit", "infrastructure_harness_errors", "infrastructure_outage",
}
MEASURED_PHASES = {"measured", "replacement"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def levels_cleared(state: dict) -> int | None:
    """Official helper semantics (baseline-harness core/bench.py levels_beaten)."""
    level = state.get("level")
    if not isinstance(level, int):
        return None
    if state.get("status") == "completed":
        mx = state.get("max_level")
        return mx if isinstance(mx, int) else None
    return max(0, level - 1)


def is_creative(state: dict) -> bool:
    return state.get("mode") == "creative"


def load_events(path: str) -> list[dict]:
    evs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                evs.append(json.loads(line))
    return evs


def tool_calls_from_stream(path: str) -> Counter:
    c = Counter()
    if not os.path.exists(path):
        return c
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(json.loads(line)["line"])
            except (ValueError, KeyError, TypeError):
                continue
            if obj.get("type") == "assistant":
                for blk in (obj.get("message") or {}).get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_use":
                        c[blk.get("name", "?")] += 1
    return c


AUDIT_TERMS = re.compile(r"dig-?bench|digbench|discos|tech_report|battleday|discovery in games|"
                         r"\bP-?(1|16|19)\b.*(rule|solution|walkthrough|guide|cheat)", re.I)


def audit_stream(path: str) -> dict:
    """Contamination audit inputs: every web lookup and every shell command mentioning a URL or a
    benchmark term. Flags are for review; classification as contaminated is a recorded decision."""
    web, flagged = [], []
    if not os.path.exists(path):
        return {"web_calls": web, "flagged": flagged}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(json.loads(line)["line"])
            except (ValueError, KeyError, TypeError):
                continue
            if obj.get("type") != "assistant":
                continue
            for blk in (obj.get("message") or {}).get("content") or []:
                if not (isinstance(blk, dict) and blk.get("type") == "tool_use"):
                    continue
                name, inp = blk.get("name", ""), blk.get("input") or {}
                text = json.dumps(inp, ensure_ascii=False)
                if name in ("WebFetch", "WebSearch"):
                    web.append({"tool": name, "input": text[:300]})
                if AUDIT_TERMS.search(text) or (name == "Bash" and re.search(r"https?://|curl|wget", text)
                                                  and not re.search(r"pypi|npmjs|pythonhosted", text)):
                    flagged.append({"tool": name, "input": text[:300]})
    return {"web_calls": web, "flagged": flagged}


def derive(run_dir: str, attempt_seconds: float = 3600.0) -> dict:
    ev_path = os.path.join(run_dir, "trusted", "events.jsonl")
    meta_path = os.path.join(run_dir, "attempt.json")
    rec: dict = {"run_dir": run_dir, "checks": {}}
    if not os.path.exists(ev_path):
        rec["checks"]["missing_trusted_log"] = True
        return rec
    evs = load_events(ev_path)
    meta = None
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    first_meta = next((e for e in evs if e["kind"] == "attempt_meta"), {})
    m = meta or first_meta
    limit = float((m.get("config") or {}).get("attempt_seconds", attempt_seconds))
    rec.update({k: m.get(k) for k in ("attempt_id", "phase", "game", "rep", "server", "synthetic")})
    rec["attempt_seconds"] = limit

    created = [e for e in evs if e["kind"] == "session_created"]
    create_reqs = [e for e in evs if e["kind"] == "create_session_request"]
    rec["session_id"] = created[0]["session_id"] if created else None
    rec["seed"] = created[0].get("seed") if created else None
    rec["framework_version"] = created[0].get("framework_version") if created else None
    rec["server_game"] = created[0].get("game") if created else None
    clock = next((e for e in evs if e["kind"] == "clock_start"), None)
    rec["clock_start_wall"] = clock["wall_start"] if clock else None
    end = next((e for e in evs if e["kind"] == "attempt_end"), None)
    rec["stop_reason"] = (end or {}).get("stop_reason") or (meta or {}).get("stop_reason")

    # ---- scored state sequence: initial state (t=0) + step results received on time
    seq = []
    if created:
        seq.append((0.0, created[0]["state"]))
    steps = [e for e in evs if e["kind"] == "step_result"]
    late = [e for e in steps if e.get("late") or (e.get("t_recv") is not None and e["t_recv"] > limit)]
    for e in steps:
        if e in late:
            continue
        seq.append((e.get("t_recv") if e.get("t_recv") is not None else e["t"], e["state"]))
    for e in evs:  # a 409 re-sync is also a server-reported state
        if e["kind"] == "resync" and e.get("t") is not None and e["t"] <= limit:
            seq.append((e["t"], e["state"]))
    seq.sort(key=lambda x: x[0])

    survival = [(t, s) for t, s in seq if not is_creative(s)]
    final = seq[-1][1] if seq else None
    final_surv = survival[-1][1] if survival else None
    comp = next(((t, s) for t, s in seq if s.get("status") == "completed"), None)
    over = next(((t, s) for t, s in seq if s.get("status") == "game_over"), None)
    rec["completed"] = comp is not None
    rec["completion_time_s"] = comp[0] if comp else None
    rec["terminal_status"] = "completed" if comp else ("game_over" if over else None)
    rec["terminal_time_s"] = (comp or over or (None,))[0]
    mx = next((s.get("max_level") for _, s in reversed(seq) if isinstance(s.get("max_level"), int)), None)
    rec["max_level"] = mx
    prog_state = (comp[1] if comp else final_surv)
    rec["levels_cleared"] = levels_cleared(prog_state) if prog_state else None
    rec["levels_cleared_normalized"] = (rec["levels_cleared"] / mx
                                        if isinstance(rec["levels_cleared"], int) and isinstance(mx, int) and mx > 0
                                        else None)
    rec["final_state_status"] = final.get("status") if final else None
    rec["final_state_mode"] = final.get("mode") if final else None

    # ---- stop time: terminal server outcome, else gate close / kill time
    gate = next((e for e in evs if e["kind"] == "gate_closed"), None)
    killed = next((e for e in evs if e["kind"] == "player_killed"), None)
    stop_t = rec["terminal_time_s"]
    if stop_t is None and gate and gate.get("t") is not None:
        stop_t = min(gate["t"], limit)
    if stop_t is None and killed and killed.get("t") is not None:
        stop_t = min(killed["t"], limit)
    rec["stop_time_s"] = stop_t

    # ---- checkpoints (derived from already-logged observations)
    closed_for_good = rec["terminal_status"] is not None or rec["stop_reason"] in (
        "player_stopped_unresolved", "player_declined_after_continuation",
        "player_ended_turn_after_continuations", "time_limit")
    cps = {}
    for cp in CHECKPOINTS:
        upto = [(t, s) for t, s in survival if t <= cp]
        c_upto = comp is not None and comp[0] <= cp
        st = comp[1] if c_upto else (upto[-1][1] if upto else None)
        if stop_t is not None and stop_t <= cp:
            coverage = "final" if closed_for_good else "last_observation_interrupted"
        else:
            coverage = "observed_through_checkpoint"
        cps[str(cp)] = {"completed": c_upto, "levels_cleared": levels_cleared(st) if st else None,
                        "coverage": coverage}
    rec["checkpoints"] = cps

    # ---- diagnostics (not stopping limits)
    diag = Counter()
    prev = seq[0][1] if seq else {}
    for e in steps:
        diag["server_steps"] += 1
        st = e["state"]
        if e.get("invalid_action"):
            diag["server_invalid_actions"] += 1
        if prev.get("creative_toggle") and e.get("action") == prev.get("creative_toggle"):
            diag["mode_toggles"] += 1
        elif is_creative(prev):
            diag["creative_mode_actions"] += 1
        else:
            diag["survival_mode_actions"] += 1
        if not is_creative(st) and not is_creative(prev):
            if isinstance(st.get("lives_left"), int) and isinstance(prev.get("lives_left"), int) \
                    and st["lives_left"] < prev["lives_left"]:
                diag["lives_lost"] += prev["lives_left"] - st["lives_left"]
        if st.get("transition"):
            diag["transitions"] += 1
        prev = st
    for e in evs:
        k = e["kind"]
        if k in ("tool_move_illegal_local", "tool_move_malformed", "tool_move_rejected", "tool_state",
                 "step_retry", "step_retry_recovered", "resync", "player_launch", "relay_hello"):
            diag[k] += 1
        if k == "dispatch":
            diag["dispatch_" + e.get("message_kind", "?")] += 1
        if k == "incident":
            diag["incident_" + e.get("type", "?")] += 1
        if k == "http" and e.get("outcome") != "ok":
            diag["http_failures"] += 1
    rec["diagnostics"] = dict(diag)
    rec["tool_calls"] = dict(tool_calls_from_stream(os.path.join(run_dir, "stream.jsonl")))
    rec["late_events"] = len(late)
    eg = [e for e in evs if e["kind"] == "egress"]
    rec["egress_hosts"] = dict(Counter(f"{e.get('host')}:{e.get('decision')}" for e in eg))
    au = audit_stream(os.path.join(run_dir, "stream.jsonl"))
    au["denied_egress"] = [e.get("host") for e in eg if e.get("decision") == "denied_benchmark_host"]
    rec["contamination_audit"] = au
    rec["needs_contamination_review"] = bool(au["flagged"] or au["denied_egress"])
    rec["contaminated"] = False

    # ---- integrity checks
    ck = rec["checks"]
    ck["duplicate_sessions"] = len(created) > 1 or len(create_reqs) > 1
    ck["missing_final_record"] = end is None or meta is None
    ck["late_events_present"] = len(late) > 0
    ck["step_sent_after_deadline"] = any(e["kind"] == "step_send" and e.get("t") is not None and e["t"] > limit
                                         for e in evs)
    ck["step_index_incidents"] = sum(1 for e in evs if e["kind"] == "incident"
                                     and e.get("type") == "step_index_contract")
    bad = []
    p = None
    for t, s in survival:
        if p is not None and isinstance(s.get("level"), int) and isinstance(p.get("level"), int):
            if s["level"] < p["level"] or s["level"] > p["level"] + 1:
                bad.append((t, p.get("level"), s.get("level")))
        p = s
    if comp and isinstance(comp[1].get("level"), int) and isinstance(mx, int) and comp[1]["level"] < mx:
        bad.append(("completed_below_max", comp[1]["level"], mx))
    ck["impossible_level_transitions"] = bad
    ck["synthetic_or_unofficial_server"] = bool(m.get("synthetic")) or (m.get("server") or "").rstrip("/") != OFFICIAL_SERVER
    ck["server_game_mismatch"] = bool(created) and created[0].get("game") not in (None, m.get("game"))
    rec["infrastructure_interrupted"] = rec["stop_reason"] in INFRA_STOPS
    return rec


def discover(runs_root: str) -> list[str]:
    out = []
    for root, dirs, files in os.walk(runs_root):
        if "events.jsonl" in files and os.path.basename(root) == "trusted":
            out.append(os.path.dirname(root))
    return sorted(out)


def fmt(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def build(manifest: dict, runs_root: str, extra_incidents: dict | None = None) -> dict:
    """Assemble measured-study tables. Only runs under <runs_root>/measured or /replacement whose
    trusted log names an official-server, non-synthetic, manifest-listed attempt are eligible."""
    entries = {a["id"]: a for a in manifest["attempts"]}
    records, rejected = [], []
    for rd in discover(runs_root):
        rel = os.path.relpath(rd, runs_root).split(os.sep)
        rec = derive(rd)
        why = []
        if rel[0] not in MEASURED_PHASES:
            why.append(f"not under measured/replacement ({rel[0]})")
        if rec.get("phase") not in MEASURED_PHASES:
            why.append(f"phase={rec.get('phase')}")
        if rec["checks"].get("synthetic_or_unofficial_server"):
            why.append("synthetic/unofficial server")
        base_id = (rec.get("attempt_id") or "").split("R")[0] if rec.get("phase") == "replacement" else rec.get("attempt_id")
        ent = entries.get(rec.get("attempt_id")) or entries.get(base_id)
        if ent is None:
            why.append("attempt id not in manifest")
        elif ent["game"] != rec.get("game") or (rec.get("phase") == "measured" and ent["rep"] != rec.get("rep")):
            why.append("manifest mismatch (game/rep)")
        if why:
            rejected.append({"run_dir": rd, "attempt_id": rec.get("attempt_id"), "why": why})
            continue
        inc = (extra_incidents or {}).get(rec["attempt_id"])
        if inc:
            rec["manual_incident"] = inc
            if inc.get("classify_as_infrastructure"):
                rec["infrastructure_interrupted"] = True
            if inc.get("contaminated"):
                rec["contaminated"] = True
        records.append(rec)
    by_id = defaultdict(list)
    for r in records:
        by_id[r["attempt_id"]].append(r)
    dupes = {k: len(v) for k, v in by_id.items() if len(v) > 1}
    missing = [a["id"] for a in manifest["attempts"] if a["id"] not in by_id]

    def summarize(recs):
        games = sorted({r["game"] for r in recs})
        per_game = {}
        for g in games:
            rs = [r for r in recs if r["game"] == g]
            k, n = sum(1 for r in rs if r["completed"]), len(rs)
            norm = [r["levels_cleared_normalized"] for r in rs]
            per_game[g] = {"n": n, "completed": k, "rate": k / n if n else None, "wilson95": wilson(k, n),
                           "levels_cleared": [r["levels_cleared"] for r in rs],
                           "max_level": sorted({r["max_level"] for r in rs if r["max_level"] is not None}),
                           "normalized": norm,
                           "mean_normalized": (sum(x for x in norm if x is not None) / len([x for x in norm if x is not None])
                                               if any(x is not None for x in norm) else None)}
        rates = [v["rate"] for v in per_game.values() if v["rate"] is not None]
        return {"per_game": per_game, "macro_completion_rate": sum(rates) / len(rates) if rates else None}

    originals = [r for r in records if r["phase"] == "measured"]
    valid = [r for r in records if not r["infrastructure_interrupted"] and not r["contaminated"]]
    return {
        "manifest_version": manifest.get("version"),
        "records": records, "rejected_runs": rejected,
        "manifest_checks": {"missing_attempts": missing, "duplicate_attempt_records": dupes},
        "all_launched": summarize(originals),
        "valid_gameplay": summarize(valid),
    }


def tables_md(res: dict) -> str:
    L = ["# Generated results (from trusted controller logs only)", ""]
    L.append("## Per-attempt record (all launched, manifest order)")
    L.append("")
    L.append("| attempt | game | rep | phase | session | seed | stop reason | completed | levels cleared / max | norm. | completion / stop time (min) | @15 | @30 | @60 | infra |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(res["records"], key=lambda r: r["attempt_id"]):
        cps = r.get("checkpoints", {})

        def cpf(k):
            c = cps.get(k, {})
            v = fmt(c.get("levels_cleared"))
            if c.get("completed"):
                v += " ✓"
            if c.get("coverage") == "last_observation_interrupted":
                v += " (last obs.)"
            return v
        t = r.get("completion_time_s") if r.get("completed") else r.get("stop_time_s")
        L.append(f"| {r['attempt_id']} | {r['game']} | {r.get('rep')} | {r['phase']} | {(r.get('session_id') or '—')[:8]} | "
                 f"{fmt(r.get('seed'))} | {r.get('stop_reason')} | {'yes' if r['completed'] else 'no'} | "
                 f"{fmt(r.get('levels_cleared'))} / {fmt(r.get('max_level'))} | {fmt(r.get('levels_cleared_normalized'))} | "
                 f"{fmt(t / 60 if t is not None else None, 1)} | {cpf('900')} | {cpf('1800')} | {cpf('3600')} | "
                 f"{'yes' if r['infrastructure_interrupted'] else 'no'} |")
    for view in ("all_launched", "valid_gameplay"):
        v = res[view]
        L += ["", f"## Completion — {view.replace('_', ' ')}", "",
              "| game | completed / n | rate | Wilson 95% CI | levels cleared (each attempt) | normalized (each) |",
              "|---|---|---|---|---|---|"]
        for g, s in v["per_game"].items():
            ci = s["wilson95"]
            L.append(f"| {g} | {s['completed']} / {s['n']} | {fmt(s['rate'])} | "
                     f"{'—' if ci is None else f'{ci[0]:.2f}–{ci[1]:.2f}'} | {s['levels_cleared']} (max {s['max_level']}) | "
                     f"{[fmt(x) for x in s['normalized']]} |")
        L.append(f"\nMacro-average completion rate (equal weight per game): {fmt(v['macro_completion_rate'])}")
    L += ["", "## Integrity", "", "```", json.dumps(res["manifest_checks"], indent=2)]
    for r in res["records"]:
        flags = {k: v for k, v in r["checks"].items() if v}
        if flags or r.get("late_events") or r.get("needs_contamination_review") or r.get("contaminated"):
            L.append(f"{r['attempt_id']}: {json.dumps(flags)} late_events={r.get('late_events')} "
                     f"contamination_review={r.get('needs_contamination_review')} contaminated={r.get('contaminated')}")
    if res["rejected_runs"]:
        L.append("rejected (not eligible for measured tables): " + json.dumps(res["rejected_runs"], indent=1))
    L.append("```")
    return "\n".join(L) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--runs", required=True)
    p.add_argument("--incidents", default=None, help="manual incident classifications (JSON)")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    manifest = json.load(open(a.manifest))
    inc = json.load(open(a.incidents)) if a.incidents and os.path.exists(a.incidents) else None
    res = build(manifest, a.runs, inc)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(a.out, "tables.md"), "w") as f:
        f.write(tables_md(res))
    print(tables_md(res))


if __name__ == "__main__":
    main()
