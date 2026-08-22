"""Irreversible engineering environments for process-reward research.

An RL environment family whose recoverability is a dial. See ../README.md and
the explainer at ../../point-of-no-return.html.
"""

from .agents import DESTRUCTIVE_PLAN, SAFE_PLAN, HazardAgent, ScriptedAgent
from .critics import (
    CachingCritic,
    ConstantCritic,
    DistilledCritic,
    OracleCritic,
    RandomCritic,
    SparkCritic,
)
from .episode import Step, Trajectory, run_episode
from .oracle import DataPairOracle
from .plans import PLANS, TaskPlans
from .protocol import action_boundaries, loss_mask, parse_turn, render_action
from .shaping import assemble_rewards, naive_shaping, potential_shaping
from .snapshot import SnapshotStore
from .state import EnvState
from .task import Task, load_task, setup_episode
from .tools import Toolbox, ToolResult

__all__ = [
    "DESTRUCTIVE_PLAN",
    "SAFE_PLAN",
    "CachingCritic",
    "ConstantCritic",
    "DataPairOracle",
    "DistilledCritic",
    "EnvState",
    "HazardAgent",
    "PLANS",
    "OracleCritic",
    "RandomCritic",
    "ScriptedAgent",
    "SnapshotStore",
    "SparkCritic",
    "Step",
    "Task",
    "TaskPlans",
    "ToolResult",
    "Toolbox",
    "Trajectory",
    "action_boundaries",
    "assemble_rewards",
    "load_task",
    "loss_mask",
    "naive_shaping",
    "parse_turn",
    "potential_shaping",
    "render_action",
    "run_episode",
    "setup_episode",
]
