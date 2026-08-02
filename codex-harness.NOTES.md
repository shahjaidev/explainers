# codex-harness.html — working notes

Handoff notes for `codex-harness.html`, written so a later session (or a human)
can resume without re-deriving the research. Delete this file if you don't want
it in the repo — nothing references it.

## What the page is

A self-contained explainer tracing OpenAI's Codex CLI harness, organised around
the design constraints the harness answers rather than as a component tour.

- **Source of truth:** `github.com/openai/codex` at commit **`2b5bdcf`**
  ("Support portable Agent Plugins throughout installation (#36544)").
- Every file path quoted on the page points at real code in that tree. Line
  counts were measured over `codex-rs/` excluding `vendor/`.
- No external requests: no CDN, no fonts, no analytics. Works offline.

## Rebuilding the research environment

```sh
git clone --depth 1 https://github.com/openai/codex.git
cd codex && git log --oneline -1     # expect 2b5bdcf if unchanged upstream
```

Upstream moves fast. If the commit has advanced, the structural claims below are
likely still true but the line numbers on the page will drift.

Measurements used in the page header:

```sh
ls -d codex-rs/*/ | wc -l                                    # 99 crates
find codex-rs -name '*.rs' | wc -l                           # 2,840 files
find codex-rs -name '*.rs' -not -path '*/vendor/*' | xargs cat | wc -l   # 1.27M
find codex-rs/core/src -name '*.rs' | xargs cat | wc -l      # 185k
find codex-rs/tui/src  -name '*.rs' | xargs cat | wc -l      # 237k
```

## The files that actually matter

Read these four and the rest is detail hanging off them:

| file | why |
|---|---|
| `codex-rs/core/src/session/turn.rs` | `run_turn` → `run_sampling_request` → `try_run_sampling_request`. The agent loop. 2,731 lines. |
| `codex-rs/core/src/tools/orchestrator.rs` | approval → sandbox select → attempt → escalate. 528 lines and it *is* the security model. |
| `codex-rs/core/src/tools/spec_plan.rs` | Computes the tool registry per request. 1,153 lines, almost entirely conditional. |
| `codex-rs/core/src/compact.rs` + `session/context_window.rs` | Compaction recipe and the two-ceiling trigger. |

Secondary, in rough order of payoff:

- `core/src/session/step_context.rs` — the per-request frozen view (12 lines, big idea)
- `core/src/mcp_tool_exposure.rs` — the `Deferred` vs `Direct` branch that drives discovery
- `core/src/tools/handlers/tool_search.rs` — BM25 index over deferred tools
- `core/src/tools/parallel.rs` — the RwLock read/write guard trick
- `core/src/safety.rs` — `assess_patch_safety`
- `core/src/guardian/` — the LLM approval reviewer
- `sandboxing/src/manager.rs` — `SandboxType`, `select_initial`, `transform`
- `rollout/src/policy.rs` — what is deliberately not persisted
- `protocol/src/protocol.rs` — `Op` (:531), `AskForApproval` (:917), `EventMsg` (:1288)

## Load-bearing facts the page asserts

Worth re-verifying if upstream moves, because these are the claims a reader
would challenge:

**Compaction**
- Trigger: `token_limit_reached = scope_tokens >= (scope_limit + fallback_buffer) || active >= full_window`
- `AutoCompactTokenLimitScope::BodyAfterPrefix` subtracts `prefill_input_tokens`
  so the cached prefix doesn't count against the budget.
- Local recipe (`compact.rs:622 build_compacted_history`): initial context +
  most recent user messages up to `COMPACT_USER_MESSAGE_MAX_TOKENS` (20,000,
  oldest one token-truncated) + summary **as a `user` message**. Reasoning,
  assistant messages and all tool items are dropped. `collect_user_messages`
  skips prior summaries via `is_summary_message` so summaries don't stack.
- Remote recipe: `should_keep_compacted_history_item` filters the *server's*
  output — drops `developer` messages and wrapper `user` messages, keeps
  assistant/user/hook-prompt/compaction items.
- Remote v2 constants: `RETAINED_MESSAGE_TOKEN_BUDGET` 64,000;
  `MAX_RETAINED_AGENT_MESSAGE_TOKENS` 10,000;
  `MAX_REMOTE_COMPACTION_V2_STREAM_RETRIES` 2.
- Fourth path: `compact_token_budget.rs` skips summarisation entirely and
  installs a fresh window, still through the compaction lifecycle.
- The placement constraint (quoted verbatim on the page) — mid-turn compaction
  must use `BeforeLastUserMessage` because the model was *trained* to see the
  summary last. This is the single best detail in the codebase.
- Prompt is `prompts/templates/compact/prompt.md` — a handoff to another LLM,
  not a recap. Receiving side is `summary_prefix.md`.

**Tool discovery**
- `mcp_tool_exposure.rs`: MCP tools register as `Deferred` iff `search_tool_enabled`,
  else `Direct`. One flag, two regimes.
- `search_tool_enabled = model_info.supports_search_tool && provider.capabilities().namespace_tools`
- `tool_search` uses the `bm25` crate (English), one document per deferred tool,
  `TOOL_SEARCH_DEFAULT_LIMIT` = 8. Not embeddings — no network, no cache.
- `ToolSearchInfo::from_spec` sets `defer_loading = true` and strips
  `output_schema`; results are immediately-callable specs, coalesced by namespace.
- Mention sigils in `utils/plugins/src/mention_syntax.rs`: `$` tools, `@` plugins,
  plus `mcp://server` paths. Resolved in `required_mcp_servers_for_input` at
  **step 2 of the turn**, before the tool plan is built — that ordering is what
  makes lazy MCP startup work.
- `ToolExposure` = Direct / Deferred / DirectModelOnly / Hidden.

**Everything else**
- Sandbox backends: Seatbelt (SBPL), Landlock+seccomp, bubblewrap, Windows
  restricted token. `get_platform_sandbox()` returns `None` on Windows unless
  explicitly enabled.
- Escalation after `SandboxErr::Denied` requires all three: real denial +
  `escalate_on_failure()` + `wants_no_sandbox_approval()`. Under `Never`/`OnRequest`
  there is no silent unsandboxed retry.
- Guardian: 90 s timeout, fails closed, `MAX_CONSECUTIVE_GUARDIAN_DENIALS_PER_TURN` = 3,
  10k-token transcript caps, inherits parent network policy.
- unified exec: 64 processes, 1 MiB buffers, 250 ms–30 s yields, 300 s background cap.
- Config precedence: MDM 0, System 10, Enterprise 15, User 20/21, Project 25,
  Session flags 30, legacy 40/50 — plus `ConfigRequirements` constraints that
  clamp higher layers (hence `Constrained<AskForApproval>`).

## Page structure

15 sections. Five interactive pieces, all vanilla JS in one IIFE at the bottom:

| id | what |
|---|---|
| `#whyList` / `#whyBody` | the seven motivating problems |
| `#stackMap` | 31-node clickable layer map |
| `#loopSteps` | 16-step turn-loop walkthrough with source excerpts |
| `#toolGrid` | filterable tool registry (27 entries) |
| `#funnel` | tool-list funnel, toggleable mechanisms |
| `#pipeDiagram` | 12-stage dispatch pipeline |
| `#simTrace` | approval/sandbox decision simulator |
| `#histBefore` / `#histAfter` | compaction history transformer |

Diagrams are hand-written inline SVG using CSS vars for theming (`.dg` class).
Theme is `prefers-color-scheme` plus a `data-theme` override on `:root`, with the
toggle persisting to `localStorage` under `codex-theme`.

## Verification workflow

The page was checked by rendering it in headless Chromium — worth repeating after
any edit, since a JS error silently blanks an interactive section:

```sh
npm i playwright
node -e '
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }); // omit locally
  const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
  const errs = [];
  p.on("pageerror", e => errs.push(String(e)));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file://" + process.cwd() + "/codex-harness.html");
  await p.waitForTimeout(600);
  console.log(await p.evaluate(() => ({
    why: document.querySelectorAll("#whyList .whyitem").length,      // 7
    stack: document.querySelectorAll("#stackMap .node").length,      // 31
    steps: document.querySelectorAll("#loopSteps .step").length,     // 16
    tools: document.querySelectorAll("#toolGrid .tcard").length,     // 27
    pipe: document.querySelectorAll("#pipeDiagram .pbox").length,    // 12
    after: document.querySelectorAll("#histAfter .hitem").length,    // 4
    overflow: document.documentElement.scrollWidth > window.innerWidth, // false
  })), errs);
  await b.close();
})();'
```

Also check dark mode (`colorScheme: "dark"`) — several SVG diagrams rely on
`var(--surface2)` fills that need contrast in both themes.

## Known limitations, stated on the page

- The approval simulator is a faithful but **simplified** model. It does not
  consult execpolicy rules, cached approvals, network-policy decisions, or
  per-tool overrides. The page says so inline; keep that disclaimer if you edit it.
- The discovery funnel numbers (141 → 22 → 2) are an *illustrative* scenario
  (6 MCP servers × 20 tools), not measured from a real session. Also labelled.

## Things left unexplored

Candidates if this ever gets a part two:

- `codex-rs/tui/` (237k lines) — barely touched here beyond naming it.
- `app-server-protocol/` v2 codegen and the experimental-field negotiation system.
- `exec-server/` remote path: Noise channel, rendezvous relay, capability roots.
- `execpolicy/` rule language itself — the page describes it but never reads the grammar.
- `rollout-trace/` and the replay-bundle tooling.
- Multi-agent v1 vs v2 differences (4,538 lines of tests were not read closely).
