"""Print a trajectory, step by step, with recoverability marked.

    python demo.py                    # destructive ordering, K=0
    python demo.py --plan safe
    python demo.py --plan destructive --undo 1
    python demo.py --plan destructive --undo inf
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from irrev import (  # noqa: E402
    PLANS,
    OracleCritic,
    ScriptedAgent,
    load_task,
    run_episode,
)

TASKS_DIR = Path(__file__).resolve().parent / "tasks"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=sorted(PLANS), default="split_address")
    ap.add_argument("--plan", choices=("safe", "destructive"), default="destructive")
    ap.add_argument("--undo", default="0", help="undo budget K, or 'inf'")
    args = ap.parse_args()

    budget = math.inf if args.undo == "inf" else float(args.undo)
    task = load_task(TASKS_DIR / args.task)
    plans = PLANS[args.task]
    plan = plans.safe if args.plan == "safe" else plans.destructive
    work = Path(tempfile.mkdtemp(prefix="irrev-demo-"))
    try:
        traj = run_episode(
            task,
            ScriptedAgent(plan),
            root=work / "ep",
            undo_budget=budget,
            critic=OracleCritic(task.oracle()),
            max_steps=task.horizon,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"task={task.name}  plan={args.plan}  K={args.undo}\n")
    header = f"{'#':>2}  {'action':<11} {'ok':<4} {'recoverable':<12} {'phi':>5} {'reward':>7}  detail"
    print(header)
    print("-" * len(header))
    for i, step in enumerate(traj.steps):
        mark = "yes" if step.recoverable else "NO"
        detail = (step.args.get("query") or step.args.get("path") or "")[:44]
        reward = traj.rewards[i] if i < len(traj.rewards) else 0.0
        phi = traj.phi[i + 1] if i + 1 < len(traj.phi) else float("nan")
        flag = "  <-- point of no return" if traj.pnr == i else ""
        print(
            f"{i + 1:>2}  {step.action:<11} {'ok' if step.ok else 'ERR':<4} "
            f"{mark:<12} {phi:>5.2f} {reward:>7.2f}  {detail}{flag}"
        )
    print()
    print(traj.summary())
    if not traj.tests_ok:
        print("\nlast test output:\n" + traj.detail.strip()[-500:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
