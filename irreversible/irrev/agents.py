"""Agents without a model.

Two scripted plans per task reproduce the trajectory pair from the explainer:
the same migration, ordered safely or destructively. :class:`HazardAgent` is
the stochastic version used by the sweep — it follows the safe plan but with
probability *h* per step takes a destructive action instead, then spends an
undo if it has one. That is precisely the generative process behind the
binomial model the study predicts, which makes the sweep an end-to-end test of
the harness that needs no GPU.

The plans themselves live in :mod:`irrev.plans`.
"""

from __future__ import annotations

import random
from typing import List, Optional

from .plans import PLANS, TaskPlans, Turn
from .protocol import render_action

# Back-compatible aliases for the first task.
SAFE_PLAN: List[Turn] = PLANS["split_address"].safe
DESTRUCTIVE_PLAN: List[Turn] = PLANS["split_address"].destructive


class ScriptedAgent:
    """Replays a fixed plan. Returns None when exhausted."""

    def __init__(self, plan: List[Turn]):
        self.plan = list(plan)
        self.i = 0

    def act(self, observation: str, ctx: dict) -> Optional[str]:
        if self.i >= len(self.plan):
            return None
        thought, name, args = self.plan[self.i]
        self.i += 1
        return render_action(name, args, thought)


class HazardAgent:
    """Safe plan, with an independent per-step probability of destroying data.

    After a destructive step it spends an undo if it has budget left — so a
    trajectory succeeds iff the number of hazards it hit was within K, which
    is ``P(Binomial(H, h) <= K)`` up to the horizon growth that undos cause.
    """

    def __init__(
        self,
        hazard: float,
        seed: int = 0,
        plans: Optional[TaskPlans] = None,
    ):
        self.plans = plans or PLANS["split_address"]
        self.hazard = hazard
        self.rng = random.Random(seed)
        self.plan = list(self.plans.safe)
        self.i = 0
        self.pending_undo = False
        self.hazards_hit = 0

    def _hazard_turn(self) -> str:
        return render_action(
            "sql", {"query": self.plans.hazard(self.i)}, "Clean up the old values first."
        )

    def act(self, observation: str, ctx: dict) -> Optional[str]:
        if self.pending_undo:
            self.pending_undo = False
            if ctx["budget_remaining"] > 0:
                return render_action("undo", {}, "That destroyed data — roll it back.")
        if self.i >= len(self.plan):
            return None
        # Never derail the final submit; keeps horizons comparable across K.
        if self.plan[self.i][1] != "submit" and self.rng.random() < self.hazard:
            self.hazards_hit += 1
            self.pending_undo = True
            return self._hazard_turn()
        thought, name, args = self.plan[self.i]
        self.i += 1
        return render_action(name, args, thought)
