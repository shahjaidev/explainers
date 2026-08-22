"""Dry-run the whole experiment with no model in the loop.

Runs the real environment — real SQLite, real destructive DDL, real snapshot
store, real oracle — driven by a stochastic scripted agent, over the same
K sweep the study will use. Two arms:

    baseline  : hazard h
    supervised: hazard h * (1 - r)     "process supervision lowers the hazard"

If the measured curve tracks the analytic one, the harness is wired correctly
and the sweep, the plots and the analysis scripts are all exercised before a
GPU is provisioned. If it doesn't, something in the oracle or the snapshot
budget is wrong, and it is much cheaper to find out here.

    python sim/sweep.py --episodes 60 --hazard 0.18 --reduction 0.5
"""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from irrev import PLANS, HazardAgent, load_task, run_episode  # noqa: E402
from sim.hazard_model import binom_cdf  # noqa: E402

TASKS_DIR = Path(__file__).resolve().parents[1] / "tasks"


def run_arm(task, plans, hazard: float, budget: float, episodes: int, seed0: int, workroot: Path):
    wins = 0
    pnrs = []
    for i in range(episodes):
        agent = HazardAgent(hazard=hazard, seed=seed0 + i, plans=plans)
        traj = run_episode(
            task,
            agent,
            root=workroot / f"ep{i}",
            undo_budget=budget,
            max_steps=task.horizon + (0 if budget == math.inf else int(budget) * 2) + 4,
        )
        wins += 1 if traj.success else 0
        if traj.pnr is not None:
            pnrs.append(traj.pnr + 1)
        shutil.rmtree(workroot / f"ep{i}", ignore_errors=True)
    mean_pnr = sum(pnrs) / len(pnrs) if pnrs else float("nan")
    return wins / episodes, len(pnrs) / episodes, mean_pnr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=str, default="split_address", choices=sorted(PLANS))
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--hazard", type=float, default=0.18)
    ap.add_argument("--reduction", type=float, default=0.5)
    ap.add_argument("--budgets", type=str, default="0,1,2,4")
    ap.add_argument("--include-inf", action="store_true", default=True)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", type=str, default="sweep.csv")
    args = ap.parse_args()

    task = load_task(TASKS_DIR / args.task)
    plans = PLANS[args.task]
    budgets = [float(b) for b in args.budgets.split(",") if b != ""]
    if args.include_inf:
        budgets.append(math.inf)

    supervised_hazard = args.hazard * (1 - args.reduction)
    plan_len = plans.length  # the effective horizon for the analytic model

    rows = []
    work = Path(tempfile.mkdtemp(prefix="irrev-sweep-"))
    try:
        for budget in budgets:
            base_win, base_pnr_rate, base_pnr = run_arm(
                task, plans, args.hazard, budget, args.episodes, args.seed, work
            )
            sup_win, sup_pnr_rate, sup_pnr = run_arm(
                task, plans, supervised_hazard, budget, args.episodes, args.seed, work
            )
            k = "inf" if budget == math.inf else int(budget)
            predicted = (
                0.0
                if budget == math.inf
                else binom_cdf(plan_len, supervised_hazard, int(budget))
                - binom_cdf(plan_len, args.hazard, int(budget))
            )
            rows.append(
                {
                    "K": k,
                    "outcome_only": round(base_win, 3),
                    "process": round(sup_win, 3),
                    "advantage": round(sup_win - base_win, 3),
                    "predicted_advantage": round(predicted, 3),
                    "died_outcome_only": round(base_pnr_rate, 3),
                    "died_process": round(sup_pnr_rate, 3),
                    "mean_pnr_outcome_only": round(base_pnr, 2),
                    "mean_pnr_process": round(sup_pnr, 2),
                }
            )
            print(
                f"K={k:>3}  outcome-only {base_win:.2f}  process {sup_win:.2f}  "
                f"advantage {sup_win - base_win:+.2f}  (predicted {predicted:+.2f})  "
                f"died {base_pnr_rate:.2f} -> {sup_pnr_rate:.2f}"
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    out = Path(args.out)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
