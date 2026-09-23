# Protocol v1: vanilla Claude Code baseline on DiG-bench P-16 and P-19

Status: **DRAFT v1**. This file becomes frozen when `manifest.json` is generated. The manifest records this file's sha256, and the scheduler refuses to run if it changes. Any later change requires a new protocol version (`protocol_v2.md` plus a new manifest). Runs made under different versions are never pooled silently.

## 1. Question and scope

The study asks what the ordinary model plus its ordinary harness does on two DiG-bench games under a 60-minute elapsed-time allowance. It has one condition only: no memory prosthetic, no self-curation or reflection instructions, no researcher reasoning advice, and no rules-informed condition. Outcomes are:

- completion;
- partial progress (levels cleared);
- repeatability across 5 independent attempts per game;
- time to progress.

It is a time-limited pilot. It does not claim that 60 minutes suffices for these games, and it does not reproduce the benchmark paper's settings.

## 2. Fixed configuration

| Item | Setting |
|---|---|
| Games (measured) | P-16 and P-19 (public listing: tier 6 and tier 7). IDs are verified against live `GET /api/agent/games` in the smoke test. |
| Repetitions | 5 fresh attempts per game, 10 total, order from a seeded permutation (seed in manifest; the seed controls order only). |
| Model | requested `claude-opus-5-5`, the model this session is configured with. The served model is recorded from the harness `init` event and from per-turn `modelUsage`. No `--fallback-model` is set, so a smaller model is never substituted silently. Whether `claude-opus-5-5` is a date-pinned snapshot is not documented here, so it is treated as possibly not version-fixed. |
| Harness | Claude Code CLI **2.1.280**, headless `claude -p --input-format stream-json --output-format stream-json --verbose`. `DISABLE_AUTOUPDATER=1` keeps the version fixed. |
| Reasoning | `--effort xhigh`, matching this environment's session setting (`CLAUDE_EFFORT=xhigh`). |
| Permissions | `--permission-mode auto` (the mode this environment's sessions run in) with `--permission-prompts none` (headless: nothing can block waiting for a human, and prompt-requiring actions are denied and logged by the harness). |
| Context management | CLI defaults: ordinary conversation history plus native auto-compaction. No override is set; the model's reported window is 1M. |
| Native memory | Auto-memory is left as the CLI default. Each attempt gets a fresh, empty `CLAUDE_CONFIG_DIR` (no CLAUDE.md, no user settings, no hooks, plugins, skills or MCP servers beyond the game server), so native memory starts empty and is discarded afterwards. |
| Tools | The CLI's default tool set (Bash, Read/Write/Edit, Task/Agent subagents, Workflow, WebSearch, WebFetch, Monitor, Cron, and so on) plus the game MCP server. **Disallowed, for isolation and not difficulty:** `RemoteTrigger`, `PushNotification`, `SendMessage`, `ListAgents`, `DesignSync`. These act outside the attempt: cloud routines, notifications to the account owner, messaging other local agents, account-level sync. |
| Settings | `permissions.deny`: WebFetch to `digbench.ai`, `api.digbench.ai`, `www.digbench.ai`. |
| Time | 60 min elapsed per attempt; up to 2 measured players at once. |
| Smoke test | P-1, at most 10 min, excluded from results. |
| Replacements | At most 2 across the study, only under §8. |

No model-call, token, cost or action ceilings are set; the games' own step and life limits bind. `--max-budget-usd` is not used.

## 3. Launch mechanism (identical for every attempt)

- **Controller.** `controller/runner.py` runs one attempt per process, manager side and outside the sandbox. It creates exactly one server session (`POST /api/agent/sessions`, `model_name=claude-code-vanilla-baseline`, `model_version=claude-opus-5-5`) before the clock starts, and the manager does not look at the game state.
- **Player home.** Each attempt gets a fresh directory `/srv/dig/<attempt>-<random>/home` containing only `work/` (cwd), an empty `.claude/` config dir, and `.gametool/`: relay, network bridge, public proxy CA certificate, MCP config, settings. `bin/game` is a CLI wrapper. The directory is deleted after artifacts are collected.
- **Sandbox** (`controller/sandbox.py`). The player runs with private PID, mount and network namespaces and all capabilities dropped (`setpriv --no-new-privs --bounding-set=-all --inh-caps=-all`), under `env -i` with an allowlisted environment.
- **Masked paths.** tmpfs masks cover `/home/user` (this repo), `/root` (manager Claude transcripts), `/tmp` (manager scratchpad), `/var/tmp`, `/mnt/user-data`, `/home/claude` and `/srv/dig`. Only the attempt's own directory is mounted back under `/srv/dig`. Under `/home/claude`, only the harness's own model-login file comes back, read-only; the container's session-ingress token, launcher settings and hooks stay hidden.
- **Other hardening** (added before any live run after the independent code audit):
  - a minimal `/dev` (null, zero, full, random, urandom, tty, a private devpts and shm) with **no block devices**, so the raw disk cannot be read around the masks;
  - a **read-only root filesystem** in the player's namespace, so no attempt can leave files for a later one; writable locations are the attempt directory, `/tmp`, `/var/tmp`, `/dev/shm` and the empty masked dirs;
  - read-only `/sys` and `/proc/sys`;
  - private IPC and UTS namespaces.
- **Why uid 0.** The player is uid 0 because the harness's own model credential in this container is root-readable only and the manager does not copy it. Isolation therefore rests on namespaces and dropped capabilities, and the probes in §9 verify it.
- **Residual exposure.** As in any ordinary Claude Code install, the player can read its own model login file.
- **Network.** The namespace has no route out. A capability-less bridge inside it forwards `127.0.0.1:3128` to the manager's egress filter (`controller/netfilter.py`). The filter:
  - accepts HTTP CONNECT only;
  - refuses `*.digbench.ai` and IP-literal targets (which would sidestep name matching);
  - forwards everything else the way this container ordinarily would (NO_PROXY hosts directly, the rest via the container's egress proxy);
  - logs every destination host to the trusted log.

  Generic resources therefore remain available (package registries, documentation via WebFetch or WebSearch, the model API).
- **Game tool.** Players get a session-scoped relay (`controller/relay.py`), exposed two ways:
  - MCP tools `make_move(action)`, `get_state()` and `stop_attempt(reason)` (server `game`);
  - the same operations as a shell command, `game move|state|stop`, so the player's own programs can act.

  The relay holds no credential. It talks over a unix socket, guarded by a per-attempt capability string, to the controller, which holds the DiG-bench token, the session id and the step index.
- **What the published minimal harness does differently.** It is a single forced `make_move` loop with no tools; the paper also ran agentic harnesses (for example Claude Code) through MCP tools scoped to one session. This apparatus keeps Claude Code's ordinary tools and context management and adapts only the move channel.

## 4. Player view and prompt

- **Initial message.** The fixed prompt is `prompts/player_prompt_v1.txt`. It has four parts:
  - the brief's fixed text, verbatim;
  - the official DiG-bench general gameplay text ("Levels, lives and steps" from Appendix A of the tech report);
  - the creative-mode block (`prompts/creative_block_v1.txt`), included only when the initial state carries `creative_toggle`, using the report's agentic-template wording with the tool name adapted;
  - the tool contract.

  Per attempt, only the game ID, the server task `description`, the initial observation, the working-directory path and the start and deadline timestamps are substituted. It is sent as the first user message; the system prompt is the CLI's own and unmodified. The benchmark's name and the manager's research are not given.
- **State slice.** The state shown to the player is exactly the official `state_for_model` slice: `observation`, `level`, `max_level`, `lives_left`, `steps_remaining`, `status`, `done`, `legal_actions`, plus `mode`, `creative_toggle` and `transition` when present. It is rendered as JSON with Unicode preserved (`ensure_ascii=False`), followed by a raw rendering of the observation. Controller extras are `invalid_action`, `note`, `elapsed_s` and `time_remaining_s`. No privileged metadata (seed, session id, step index) is shown.
- **Legal-action guard.** As in the official harness, an action that is not in a non-empty `legal_actions` list is answered locally as `invalid_action: true` without a server call. Server-side `invalid_action` no-ops are passed through.

## 5. Stepping, retries and session creation

- **Serialization.** All tool routes are serialized by one controller lock.
- **Step index.** The controller sends `step_index = last server-returned index + 1`. On a transport error, timeout, 408, 429 or 5xx it resends the **same** index. Per the documented contract the server replays the cached response, so an action is never applied twice. Backoff is `min(2^k, 30)` s, capped by the remaining attempt time, with at most 10 tries.
- **409.** A 409 (index mismatch) triggers a resync from `GET /sessions/{id}` if that route exists (checked in the smoke test), and is logged as an incident.
- **Session creation.** It is never retried automatically. An ambiguous create (a transport error or timeout after sending) is logged and the attempt ends as `infrastructure_session_create_ambiguous`. Any replacement then follows §8. No instance is ever chosen by inspecting its state.

## 6. Timing and stopping

- **Clock start.** Before dispatch, the controller waits up to 90 s for the harness to start its MCP game server. The monotonic clock starts at dispatch of the complete initial prompt with the first permitted state, and wall-clock UTC is recorded too. Setup and queue time are not player time. Model latency, local computation, tool use, rate-limit waits and retries all count.
- **Deadline** (t = 3600 s). The gate closes without waiting on any in-flight request: no further server requests are sent, and any tool call answers "closed". The player's namespace is SIGKILLed at once (all descendants die), before the controller waits for any in-flight HTTP response, which is then logged as late. Artifacts are then collected. There is no post-deadline bookkeeping grace.
- **Clock precision.** The prompt is rendered before the clock starts, so the clock covers only inserting the timestamps and the write to the player's stdin.
- **Late responses.** A step sent before the deadline whose response arrives after it is logged as `late` and never contributes to the score.
- **Terminal outcomes.**
  - The game ends early on server `status == "completed"` or `"game_over"`, or when the player calls `stop_attempt`. The gate closes at once and the terminal time is the server response time.
  - The player may then finish its final report for up to 120 s, recorded separately; it cannot affect the score.
- **Neutral continuations** (`prompts/continuation_v1.txt`). If the player ends a turn while the game is live and time remains, it receives the fixed continuation (current state and remaining time), at most **2 per attempt**.
  - If a turn that followed a continuation made no game-tool request, the player is treated as having declined: stop reason `player_declined_after_continuation`.
  - After both continuations are used, the next live turn end gives stop reason `player_ended_turn_after_continuations`.
- **Harness failures** (incident policy, applied identically to all attempts).
  - A turn ending in an API or harness error gets the same neutral continuation from a separate budget of 3, logged as `harness_error_turn`. Beyond that the stop reason is `infrastructure_harness_errors`.
  - An unexpected CLI exit is resumed with `--resume <same session>` plus the neutral continuation, at most 2 times, logged as `harness_exit_resume`. Beyond that the stop reason is `infrastructure_harness_exit`.
  - The server game session is never restarted.
  - Slow inference is never an infrastructure failure.
  - A documented, unrecoverable outage of the benchmark server (for example repeated 5xx exhausting retries) is classified `infrastructure_outage` by a manual entry in `runs/measured/incidents.json` citing the logged evidence. The entry is written before looking at the attempt's progress.

## 7. Scoring (automatic, from trusted logs only)

- **Source of truth.** Scores come only from `runs/<phase>/<id>/trusted/events.jsonl`, written by the controller. Player prose, notes and files never enter a score.
- **Primary metric.** Completion is true only if a server state with `status == "completed"` was received on time.
- **Secondary metric.** Levels cleared uses the official helper: `max_level` if completed, else `level − 1`. It is taken from the last on-time survival-mode state, because creative-mode states are excluded from progress. Raw values, `max_level` and the normalized value are reported. Missing fields stay missing.
- **Time.** Completion time is reported for wins, stop time otherwise.
- **Checkpoints.** 15, 30 and 60 min, derived from logged observations. A terminal or closed game keeps its final result, and interrupted data is labelled "last observation".
- **Diagnostics.** These are counts only, not limits: server steps, invalid actions, mode toggles, creative-mode actions, lives lost, transitions, tool calls by name, retries, incidents, continuations, egress destinations.
- **Integrity checks:**
  - duplicate sessions;
  - late events;
  - steps sent after the deadline;
  - a missing final record;
  - impossible level transitions;
  - step-index contract incidents;
  - a manifest mismatch;
  - a synthetic or unofficial server.

  Synthetic, smoke and unlisted runs can never enter the measured tables.
- **Tables.** Per-game completions k/5 with Wilson 95% intervals, and a macro-average with equal game weight. Partial progress is reported separately (individual values), so it cannot stand in for completion.

## 8. Infrastructure exclusions and replacements

- **Infrastructure-interrupted** means stop reason `infrastructure_*`, or a manual `infrastructure_outage` classified under §6.
- **Not infrastructure:** time limits, losses, voluntary stops, declines, harness permission denials and slow inference are gameplay outcomes.
- **Replacements.** At most 2 across the study, each linked to its original (`M03R1` replaces `M03`), listed in `replacements.json` and run after the planned slots.
- **Reporting.** Originals are always retained. Two views are reported:
  - **all-launched:** the 10 originals, with infrastructure failures counted as not completed;
  - **valid-gameplay:** infrastructure-interrupted originals excluded and valid replacements included.

  The best of several attempts is never selected.
- **Stopping the study.** If repeated infrastructure failure makes the results unreliable, the study stops, is repaired under a new protocol version, and the partial results are reported.

## 9. Validation before measurement

- **Local tests** (`python3 -m unittest discover -s tests -v`) cover:
  - fixture server: completion, game over, partial progress, missing state, dropped response (no double apply), 5xx retry, 409 resync, malformed and illegal actions, bad capability, ambiguous create (no retry), deadline gate, late response not scored, player stop, creative progress excluded;
  - grader guards: claimed win ignored, synthetic run rejected, manifest mismatch, duplicate session and impossible transition flags;
  - relay: MCP and CLI;
  - runner policy with a scripted player: continuation and decline, two continuations, resume after exit, deadline kill of a SIGTERM-ignoring tree with a detached child;
  - sandbox probes:
    - markers in the manager, scratchpad, sibling, shared and `/home/claude` locations are invisible;
    - no capabilities and a private PID view;
    - masks cannot be removed;
    - no block devices and no raw-disk read;
    - the root filesystem and `/proc/sys` are read-only, while the home directory and `/tmp` are writable;
    - the session-ingress token and launcher settings are hidden, and the harness login is present but read-only;
    - no raw egress and no direct upstream-proxy access;
    - benchmark hosts and IP literals are refused, and pypi is reachable through the filter.
- **Synthetic real-model runs** (runs/synthetic, excluded): a real sandboxed player completed the fixture game through MCP.
- **Smoke test.** An excluded P-1 run of at most 10 minutes on the live service, followed by a live contract audit on that session only: `GET /games` IDs, the `GET /sessions/{id}` route, idempotent replay of an applied index, and the stale-index code.

## 10. Contamination rule

- **Automatic audit.** Every egress destination, WebFetch or WebSearch call and Bash command is audited after each attempt. Any hit on benchmark names or hosts (`digbench`, `dig-bench`, `discos-research`, the report, the game ID next to a lookup) flags the attempt for review.
- **If contaminated.** An attempt that obtained forbidden game-specific information (rules, solutions, benchmark analyses, other players' work, hidden state, or extra sessions) is flagged **contaminated** and reported, whatever its outcome. It is kept in all-launched and excluded from the valid-gameplay view.
- **Manager separation.** The manager's privileged research never enters player-visible storage.
