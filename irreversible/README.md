# Irreversible engineering environments

An RL environment family whose **recoverability is a dial**, built to test one
claim: process reward models beat outcome-only RL because environments are
irreversible, not because dense rewards are easier to learn from. If that is
right, the PRM advantage should be largest at undo budget `K = 0` and vanish
as `K` grows past the expected number of destructive steps.

The write-up is [`../point-of-no-return.html`](../point-of-no-return.html).
This directory is the part you can run.

Everything here is stdlib Python 3.9+. No dependencies, no Docker, no GPU.

```
python -m unittest discover -s tests -t .     # 47 tests
python demo.py --plan destructive --undo 0    # watch a trajectory die
python sim/sweep.py --episodes 40             # the K sweep, no model in the loop
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

## The task

`tasks/split_address/` is Harbor-shaped — Dockerfile + instruction + test.
Move a free-text `users.address` column into a dedicated `addresses` table,
backfill, drop the column, keep the application working. Success is two
machine-checked conditions with no judge anywhere:

- `repo/verify.py` passes (structure + `app.get_address` still works), and
- the protected pairs are still in the database (harness-side, so the agent
  cannot fake it by leaving a dump on disk).

The destructive step is real: `ALTER TABLE users DROP COLUMN address` with no
copy anywhere is unrecoverable at `K=0`, and the oracle says so.

The local backend uses SQLite so the whole harness runs anywhere. The
`Dockerfile` is the container path; for Postgres, swap the snapshot backend
for `pg_dump`/PITR and the overlayfs upper dir — `SnapshotStore` is the only
class that needs to change.

## Does the harness reproduce the prediction?

`sim/sweep.py` runs the real environment — real SQLite, real destructive DDL,
real snapshots, real oracle — driven by a scripted agent that hits a hazard
with probability *h* per step and spends an undo if it has one. "Process
supervision" is modelled as a lower hazard. No model, no GPU, no teacher.

40 episodes per arm, `h = 0.18`, `r = 0.5`:

| K | outcome-only | process | advantage | predicted | died (base → process) |
|---|---|---|---|---|---|
| 0 | 0.23 | 0.45 | **+0.23** | +0.27 | 0.78 → 0.55 |
| 1 | 0.65 | 0.90 | **+0.25** | +0.28 | 0.35 → 0.10 |
| 2 | 0.88 | 1.00 | **+0.12** | +0.13 | 0.12 → 0.00 |
| 4 | 0.93 | 1.00 | **+0.07** | +0.01 | 0.07 → 0.00 |
| ∞ | 1.00 | 1.00 | **+0.00** | +0.00 | 0.00 → 0.00 |

The shape is what the hypothesis predicts: large advantage at small budgets,
exactly zero when the agent can always undo. Two honest caveats:

- **K=0 and K=1 are not separated** at this sample size (n=40, standard error
  ≈ 0.08). The first two points are within noise of each other; only the decay
  across the whole sweep is meaningful here.
- **K=4 deviates from the analytic curve** (+0.07 measured, +0.01 predicted).
  This is not noise, it is a modelling gap worth keeping: each undo adds two
  steps to the episode, and those steps carry their own hazard. Spending
  budget lengthens the horizon, which creates more chances to need budget. The
  binomial model assumes a fixed horizon and misses it. If the same signature
  shows up with a real policy, it is a finding rather than an artefact.

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
  agents.py      scripted safe/destructive plans; stochastic HazardAgent
  episode.py     the runner that measures the point of no return
  task.py        task loading, episode setup, protected-pair extraction
adapters/
  verifiers_env.py     StatefulToolEnv + Rubric, Environments Hub entry point
  prime_rl_shaping.py  turn potentials -> shaped returns -> group-relative
                       advantages -> per-token broadcast over action spans
tasks/split_address/   Dockerfile + instruction + test + seed
sim/                   analytic model, and the K sweep that exercises it
tests/                 47 tests, stdlib unittest
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
- More tasks. One task is enough to validate the machinery and nowhere near
  enough to train on. The next ones — polymorphic-association collapse,
  index-drop with a planner dependency, a backfill that must be resumable —
  reuse everything except `seed.sql`, `verify.py` and the protected query.
