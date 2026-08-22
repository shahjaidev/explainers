# Irreversible engineering environments

An RL environment family whose **recoverability is a dial**, built to test one
claim: process reward models beat outcome-only RL because environments are
irreversible, not because dense rewards are easier to learn from. If that is
right, the PRM advantage should be largest at undo budget `K = 0` and vanish
as `K` grows past the expected number of destructive steps.

The write-up is [`../point-of-no-return.html`](../point-of-no-return.html).
This directory is the part you can run.

Core is stdlib Python 3.9+. No dependencies, no Docker, no GPU.

```
python -m unittest discover -s tests -t .              # 69 tests (9 skip without verifiers)
python demo.py --task split_address --plan destructive # watch a trajectory die
python sim/sweep.py --task merge_duplicate_users       # the K sweep, no model in the loop
```

## What a trajectory looks like

```
$ python demo.py --plan destructive --undo 0

 #  action      ok   recoverable    phi  reward  detail
-------------------------------------------------------
 1  sql         ok   yes           1.00    0.00  SELECT id, name, address FROM users LIMIT 3
 2  sql         ok   NO            0.00   -1.00  ALTER TABLE users DROP COLUMN address;  <-- point of no return
 3  sql         ok   NO            0.00    0.00  CREATE TABLE addresses (id INTEGER PRIMARY K
 4  sql         ERR  NO            0.00    0.00  INSERT INTO addresses (user_id, line) SELECT
 5  write_file  ok   NO            0.00    0.00  app.py
 6  run_tests   ERR  NO            0.00    0.00
 7  sql         ok   NO            0.00    0.00  SELECT * FROM addresses LIMIT 3
 8  run_tests   ERR  NO            0.00    0.00
 9  sql         ok   NO            0.00    0.00  PRAGMA table_info(users)
10  submit      ok   NO            0.00    0.00

split_address K=0 steps=10 tests=fail integrity=lost undos=0 point-of-no-return=step 2
```

Steps 3–10 are generated from a state the task can no longer be completed
from. Outcome-only RL assigns all eight the same negative advantage as step 2,
which is the one that actually caused it. That is the waste the study is about.

Run the same plan with `--undo 1` and the point of no return moves to step 3 —
one undo buys exactly one step of grace, and this agent never spends it. With
`--undo inf` it disappears entirely.

## The three tasks

Each ships a safe and a destructive ordering of the same migration. Same
model, same actions, different order — only one leaves the recoverable set.

| task | migration | destruction | invariant |
|---|---|---|---|
| `split_address` | free-text column → its own table | all-or-nothing: drop before backfill and the column is gone | `(user, address)`, in-row |
| `merge_duplicate_users` | dedupe by email, repoint orders | **partial**: deleting duplicates before repointing orphans only the orders that pointed at them — φ lands on 0.6, not 0 | `(order, email)`, only across a join |
| `collapse_polymorphic` | `(parent_type, parent_id)` → typed FK columns | all-or-nothing, but the invariant is an attribution and the discriminator can be lost separately from the data | `(parent, body)`, in-row |

The middle one exists to make sure the harness handles gradual degradation:
a task whose potential slides is a different test of a shaping signal than one
that falls off a cliff.

## The three pieces that aren't in any framework

**1. Snapshot store with a budget** (`irrev/snapshot.py`, `irrev/tools.py`).
A snapshot is taken before every action, so `undo` restores the state the last
action was taken from — except before `undo` itself, which would make it a
no-op. The budget `K` caps how many snapshots the agent can still reach.
`K=0` is a production console at 2am; `K=inf` is every RL environment ever
published.

**2. Recoverability oracle** (`irrev/oracle.py`). After each step: *is the
target still reachable?* Decided over environment state, never by a model. A
set of protected `(key, value)` pairs — extracted from the seed database
before the agent touches anything — must remain derivable from the live
database, or a file in the working tree, or a snapshot still within budget.

That last clause is the point: **recoverability is a function of K**, so the
point of no return moves as the budget grows. Nothing about the policy is
assumed.

Two strictnesses, deliberately different:

| question | sources | used for |
|---|---|---|
| `intact_in_db` | live database only | the integrity half of the outcome reward |
| `intact_now` / `recoverable` | database + working tree + reachable snapshots | the point-of-no-return measurement |

A CSV the agent dumped counts as recoverable but not as a completed migration.

Three rules the tasks forced, each of which was a real false positive first:

- **Declared recovery queries.** `(order, email)` is not a fact about any
  single row, so a task can declare SQL that reconstructs its pairs. A query
  that no longer parses against the current schema contributes nothing, which
  is the right answer.
- **A task that declares recovery queries opts out of the generic row scan.**
  `orders.id` and `users.id` share a numeric namespace, so the users row
  `(1, 'ada@…')` pattern-matches the pair `('1', 'ada@…')` — a coincidence,
  not a recovery path. Without this, destroying `orders` looked survivable.
- **Pristine template files don't count.** `merge_duplicate_users`' own
  `verify.py` asserts against a real customer email and happens to have a `2`
  on the same line, which scored as "order 2 is recoverable from disk" and
  inflated the surviving fraction from 0.6 to 0.7. Files the agent hasn't
  touched (matched by content hash) are skipped; the moment it edits one, it
  counts again.

**3. Potential-based shaping** (`irrev/shaping.py`). Teacher step scores are a
potential function: `F_t = gamma * phi(s_t+1) - phi(s_t)`, not raw score.
Policy-invariant by Ng, Harada & Russell (1999) — it can change how fast you
learn, provably not what you learn toward. `naive_shaping` is the ablation
arm; the predicted failure is an agent that narrates confidently and acts
badly, because the critic reads a well-formed `<thought>` before the action
executes.

`tests/test_adapters.py` demonstrates the guarantee end to end: two rollouts
with the same outcome and the same start/end potential get *identical*
advantages at turn 0 no matter how the potential moved in between, while the
credit inside each rollout lands on different turns.

## Does the harness reproduce the prediction?

`sim/sweep.py` drives the real environment with a scripted agent that hits a
destructive action with probability *h* per step and spends an undo if it has
one. "Process supervision" is modelled as a lower hazard. No model, no
teacher, no GPU.

40 episodes per arm, `h = 0.18`, `r = 0.5`:

| K | split_address | merge_duplicate_users | collapse_polymorphic | analytic |
|---|---|---|---|---|
| 0 | +0.23 | +0.22 | +0.23 | +0.27 |
| 1 | +0.25 | +0.18 | +0.25 | +0.28 |
| 2 | +0.12 | +0.07 | +0.12 | +0.13 |
| 4 | +0.07 | +0.00 | +0.07 | +0.01 |
| ∞ | +0.00 | +0.00 | +0.00 | +0.00 |

The shape is what the hypothesis predicts on all three: large advantage at
small budgets, exactly zero when the agent can always undo. Three honest
caveats:

- **K=0 and K=1 are not separated** at this sample size (n=40, standard error
  ≈ 0.08). Only the decay across the whole sweep is meaningful here.
- **K=4 deviates from the analytic curve** on the two 8-step tasks (+0.07
  measured, +0.01 predicted). This is not noise, it is a modelling gap worth
  keeping: each undo adds two steps to the episode, and those steps carry
  their own hazard. Spending budget lengthens the horizon, which creates more
  chances to need budget. The binomial model assumes a fixed horizon and
  misses it. If the same signature shows up with a real policy, it is a
  finding rather than an artefact.
- **`split_address` and `collapse_polymorphic` produce identical numbers**,
  because the synthetic agent's hazard draws depend only on the seed and the
  plan length, and both plans are 8 steps. These are not three independent
  samples. A real policy would separate them; this agent cannot.

This is a dry run of the analysis pipeline, not evidence about PRMs. It shows
the harness measures what it claims to measure, before anyone provisions a
GPU.

## Layout

```
irrev/
  state.py       episode paths; snapshots live outside the agent's reach
  snapshot.py    snapshot/restore, and which snapshots K still reaches
  oracle.py      recoverability + integrity, decided over env state
  tools.py       sql / read_file / write_file / list_files / run_tests / undo / submit
  protocol.py    Glimmer <thought>/<action>/<observation> parsing, loss mask,
                 action boundaries (the scoring points)
  shaping.py     potential-based shaping, the naive ablation, reward assembly
  critics.py     Spark | distilled | oracle-proxy | random, plus prefix caching
  plans.py       safe and destructive orderings per task, and the hazard
  agents.py      ScriptedAgent, stochastic HazardAgent
  episode.py     the runner that measures the point of no return
  task.py        task loading, episode setup, protected-pair extraction
adapters/
  verifiers_env.py     StatefulToolEnv + Rubric, Environments Hub entry point
  prime_rl_shaping.py  turn potentials -> shaped returns -> group-relative
                       advantages -> per-token broadcast over action spans
tasks/                 three Harbor-shaped tasks: Dockerfile + instruction + test
sim/                   analytic model, and the K sweep that exercises it
tests/                 69 tests, stdlib unittest
```

## The verifiers adapter

Written and **tested against verifiers 0.3.0**, whose contract differs from
what the docs imply in three places worth knowing:

- `args_to_skip` is an argument to `add_tool(tool, args_to_skip=[...])`, not to
  the constructor;
- `update_tool_args(tool_name, tool_args, messages, state, **kwargs)` takes the
  tool name first;
- the env wraps your `Rubric` in a `RubricGroup` alongside its own monitors, so
  `env.rubric.rubrics[0].funcs` is where your reward functions end up.

The sandbox handle lives in `state`, not a module-level registry, so concurrent
rollouts cannot collide. `tests/test_verifiers_adapter.py` checks the part that
actually matters — that `handle` is absent from every tool schema the agent
sees and injected at call time — and drives a full migration through
`env.tool_map` to confirm the rubric scores 1.0 on the safe plan and 0.0 with
`survived == 0` on the destructive one. No model required:

```
python -m venv .venv && .venv/bin/pip install verifiers
.venv/bin/python -m unittest discover -s tests -t .    # 69 tests, 0 skipped
```

## How this maps onto the frameworks

| layer | project | what we add |
|---|---|---|
| environment | **Harbor** — Dockerfile + instruction + test | snapshots, undo budget, oracle |
| training | **SkyRL** — long-horizon multi-turn agents in containers | `skyrl_advantage_fn` |
| env API | **verifiers** — `StatefulToolEnv` injects the sandbox handle | `adapters/verifiers_env.py` |
| credit assignment | **prime-rl** Algorithms layer | `prime_rl_algorithm` |

Per-turn credit assignment is not first-class in any of them — prime-rl's
layer is per-token over a finalised rollout, verifiers Rubrics collapse to one
scalar per rollout, SkyRL concatenates turns with masks. `adapters/` does the
turn → token expansion explicitly, in plain lists, so it can be dropped into
whichever trainer wins.

## Not implemented here

- The RL training loop. Use SkyRL or prime-rl; `adapters/` is the seam.
- Real teacher calls. `SparkCritic` and `DistilledCritic` are wired against
  OpenAI-shaped endpoints and refuse to run without an API key, since Muse
  Spark 1.2 weights are not public. `OracleCritic` is a free proxy potential
  for pilots; it sees privileged state, so it is a ceiling, not a stand-in.
- Postgres. The local backend is SQLite so the harness runs anywhere; the
  `Dockerfile`s are the container path. For Postgres, swap the snapshot backend
  for `pg_dump`/PITR plus the overlayfs upper dir — `SnapshotStore` is the only
  class that changes.
- Task-level unrecoverability that is not data loss. Dropping
  `collapse_polymorphic`'s `parent_type` before the backfill leaves the bodies
  and parent ids intact but makes the migration impossible; the outcome reward
  catches it, the point-of-no-return measurement does not.
