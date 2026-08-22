"""The episode runner — where the point of no return is measured.

Order of operations per step, and each line matters:

1. snapshot the pre-action state (except before ``undo``, which would make
   the undo a no-op);
2. let the agent act;
3. execute the tool;
4. ask the oracle whether the target is *still reachable given the undos the
   agent has left*;
5. score the prefix with the critic, at the ``</action>`` boundary.

The first step at which (4) is false is the trajectory's point of no return.
It is a property of the environment and the budget, not of the reward.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol

from .critics import Critic
from .oracle import DataPairOracle
from .protocol import parse_turn, render_observation
from .shaping import assemble_rewards
from .snapshot import SnapshotStore
from .state import EnvState
from .db import Database
from .task import Task, setup_episode
from .tools import Toolbox


class Agent(Protocol):
    def act(self, observation: str, ctx: dict) -> Optional[str]: ...


@dataclass
class Step:
    index: int
    thought: str
    action: str
    args: dict
    ok: bool
    observation: str
    recoverable: bool
    fraction: float
    budget_left: float


@dataclass
class Trajectory:
    task: str
    undo_budget: float
    steps: List[Step] = field(default_factory=list)
    transcript: List[str] = field(default_factory=list)
    phi: List[float] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)
    tests_ok: bool = False
    integrity_ok: bool = False
    undo_used: int = 0
    pnr: Optional[int] = None
    detail: str = ""

    @property
    def outcome(self) -> float:
        return 1.0 if (self.tests_ok and self.integrity_ok) else 0.0

    @property
    def success(self) -> bool:
        return self.tests_ok and self.integrity_ok

    def summary(self) -> str:
        budget = "inf" if self.undo_budget == math.inf else int(self.undo_budget)
        pnr = "none" if self.pnr is None else f"step {self.pnr + 1}"
        return (
            f"{self.task} K={budget} steps={len(self.steps)} "
            f"tests={'pass' if self.tests_ok else 'fail'} "
            f"integrity={'ok' if self.integrity_ok else 'lost'} "
            f"undos={self.undo_used} point-of-no-return={pnr}"
        )


def run_episode(
    task: Task,
    agent: Agent,
    root: Path,
    undo_budget: float = 0,
    critic: Optional[Critic] = None,
    max_steps: Optional[int] = None,
    gamma: float = 1.0,
    shaping: str = "potential",
    allow_shell: bool = False,
    database: Optional[Database] = None,
) -> Trajectory:
    state, oracle = setup_episode(task, Path(root), database=database)
    store = SnapshotStore(state)
    tools = Toolbox(state, store, undo_budget=undo_budget, allow_shell=allow_shell)

    traj = Trajectory(task=task.name, undo_budget=undo_budget)
    traj.transcript.append(task.instruction)
    if critic is not None:
        traj.phi.append(critic.score(state, traj.transcript, task.name))

    limit = max_steps if max_steps is not None else task.horizon
    observation = task.instruction

    for t in range(limit):
        ctx = {
            "step": t,
            "budget_remaining": tools.budget_remaining,
            "steps_left": limit - t,
        }
        turn = agent.act(observation, ctx)
        if not turn:
            break
        thought, name, args = parse_turn(turn)
        if name is None:
            break

        if name != "undo":
            store.take(label=f"step {t + 1} ({name})")

        result = tools.call(name, args)
        observation = result.output
        traj.transcript.append(turn)
        traj.transcript.append(render_observation(observation))

        recoverable = oracle.recoverable(state, store, tools.budget_remaining)
        if traj.pnr is None and not recoverable:
            traj.pnr = t

        traj.steps.append(
            Step(
                index=t,
                thought=thought,
                action=name,
                args=args,
                ok=result.ok,
                observation=observation[:2000],
                recoverable=recoverable,
                fraction=oracle.fraction_now(state),
                budget_left=tools.budget_remaining,
            )
        )
        if critic is not None:
            traj.phi.append(critic.score(state, traj.transcript, task.name))
        if result.submitted:
            break

    tests = tools.call("run_tests", {})
    traj.tests_ok = tests.ok
    traj.detail = tests.output[-1500:]
    traj.integrity_ok = oracle.intact_in_db(state)
    traj.undo_used = tools.undo_used

    if critic is not None and len(traj.phi) >= 2:
        traj.rewards = assemble_rewards(traj.outcome, traj.phi, gamma=gamma, mode=shaping)
    else:
        traj.rewards = [0.0] * max(0, len(traj.steps) - 1) + [traj.outcome]

    return traj
