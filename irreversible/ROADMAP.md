# What it takes to run the training end to end

The environment is done and tested. What is missing is everything between a
policy's tokens and this harness's `act()`. In rough dependency order.

## 1. Token-level plumbing (the actual blocker)

`run_episode` drives a Python `Agent` protocol. A trainer needs, per rollout:
token ids, a loss mask, and the token span of every `</action>` boundary — that
last one is where the potential goes and where the advantage lands.

`irrev/protocol.py` computes boundaries and the mask over *characters*. Turning
those into token spans needs the tokenizer's offset mapping, applied once per
turn as the transcript is built. Concretely:

- a `TokenizingAgent` that wraps a vLLM chat endpoint, records
  `(start, end)` token offsets for each assistant action span, and returns the
  raw turn text the harness already parses;
- `loss_mask` lifted from characters to tokens through the same offsets;
- a test asserting no `<observation>` token is trainable and that the boundary
  count equals the number of steps.

Everything downstream — `adapters/skyrl_advantage.py`, `prime_rl_shaping.py` —
already consumes exactly this shape. Nothing else in the repo changes.

## 2. Pick one trainer and wire it

**Recommendation: prime-rl + verifiers first.** The verifiers adapter is
tested against the real library, prime-rl has first-class verifiers support,
LoRA, and an Algorithms layer that is the natural home for the shaping. SkyRL +
Harbor is the better long-run home for container-based tasks, but its
advantage estimator is only source-verified here (`flash-attn` needs `nvcc`, so
skyrl-train would not install), and Harbor wants the Dockerfiles built, which
has never been done.

Either way the work is: package the env for the Environments Hub
(`adapters/verifiers_env.py:load_environment` is the entry point), register the
shaped estimator, and confirm a 2-rollout smoke run produces non-zero
advantages on the action spans and zeros everywhere else.

## 3. Models

- **Policy — Muse Glimmer 30B.** Dense 29.6B, so bf16 weights shard fine across
  4×H100 with LoRA adapters. Drop the 4-bit QLoRA idea for the training arm;
  these trainers shard bf16 over FSDP and do not expect a quantised base.
- **Teacher — Muse Spark 1.2.** Weights are not public. Check the Foundry
  catalog; otherwise `SparkCritic` points at any OpenAI-shaped endpoint and
  refuses to run without `TEACHER_API_KEY`.

## 4. The critic pipeline, because Spark cannot be in the loop

Ten boundaries per rollout × 32k rollouts × ~8k context is billions of teacher
tokens per run. The path that works:

1. run a few hundred episodes with the SFT policy, `CachingCritic` wrapping
   `SparkCritic`, writing its JSONL label log (already implemented);
2. train a small critic on those labels — 8B, or a value head on frozen
   Glimmer;
3. serve it and point `DistilledCritic` at it;
4. plot downstream RL performance against the number of Spark labels. That
   curve is the most reusable result in the study.

`OracleCritic` is free and needs no model, so the plumbing can be validated
end to end before any teacher spend. It sees privileged state, so treat it as a
ceiling, never as a result.

## 5. Throughput

Measured on this harness: an episode is dominated by environment work, not by
the model.

- **Use SQLite for the training runs.** A snapshot is a file copy; the Postgres
  path runs `pg_dump` *per step* and `pg_restore` into a scratch database
  whenever the oracle inspects a snapshot. Keep Postgres for validation runs
  that confirm the two backends agree — they do, and there is a test for it.
- Run environments on separate hosts from the trainer, many workers, and reuse
  Postgres `CREATE DATABASE ... TEMPLATE` rather than re-seeding when the
  Postgres path is used.
- `run_tests` shells out to a Python subprocess per call. At scale that wants a
  resident worker.

## 6. Task supply

Three tasks validate the machinery and are nowhere near enough to train on. The
generator to write: schema templates × migration types × seeds, each emitting
`seed.sql`, a protected query, recovery queries, and a `verify.py`. Aim for a
few hundred, split by *template family* so an evaluation task is never a reskin
of a training one — the same source-group discipline that keeps clip-level
leakage out of a motion dataset.

## 7. Measurement

The point-of-no-return index is recorded per trajectory (`Trajectory.pnr`) and
per step (`Step.recoverable`). Log both to the trainer's metrics per rollout,
or the mechanism plot cannot be produced after the fact.

## Staging

1. **Week 1** — token plumbing, `OracleCritic`, one task, K=0 only. Success
   criterion: advantages land on action spans and nowhere else.
2. **Week 2** — the K=0 vs K=∞ endpoints at small scale. If the gap does not
   appear where the model says it should be largest, it is not there, and this
   is where you find out cheaply.
3. **Week 3** — the sweep plus the compute-matched arm.
4. **Week 4** — Spark labels, distilled critic, the label-count curve.

`sim/sweep.py` already produces the exact table shape the study needs, with a
scripted agent standing in for the policy. Swap the agent, keep the analysis.
