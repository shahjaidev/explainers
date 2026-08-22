"""verifiers adapter — publishing the environment to the Environments Hub.

``StatefulToolEnv`` is the right base class for this: it lets tool functions
take parameters that are injected by the environment and hidden from the
model's tool schema (``args_to_skip``), which is exactly what an episode
handle is. The agent sees ``sql(query)``; the environment supplies which
container it runs against.

One thing the verifiers abstraction does not give us: a Rubric collapses to a
single scalar per rollout, so the process potential cannot live there. Rubric
below carries the *outcome* reward only — tests plus integrity — and the
per-step potential is attached as rollout metadata for the trainer's advantage
function to consume. See ``prime_rl_shaping.py``.

Import-guarded so the rest of the package works without verifiers installed.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from irrev.critics import Critic
from irrev.oracle import DataPairOracle
from irrev.snapshot import SnapshotStore
from irrev.task import Task, load_task, setup_episode
from irrev.tools import Toolbox

try:  # pragma: no cover - exercised only where verifiers is installed
    import verifiers as vf

    _HAVE_VERIFIERS = True
except ImportError:  # pragma: no cover
    vf = None
    _HAVE_VERIFIERS = False


TASKS_DIR = Path(__file__).resolve().parents[1] / "tasks"


class EpisodeHandle:
    """Per-rollout state: the sandbox handle that never reaches the model."""

    def __init__(self, task: Task, root: Path, undo_budget: float):
        self.task = task
        self.state, self.oracle = setup_episode(task, root)
        self.store = SnapshotStore(self.state)
        self.tools = Toolbox(self.state, self.store, undo_budget=undo_budget)
        self.undo_budget = undo_budget
        self.pnr: Optional[int] = None
        self.step = 0
        self.potentials: List[float] = []

    def execute(self, name: str, args: Dict[str, str]) -> str:
        if name != "undo":
            self.store.take(label=f"step {self.step + 1} ({name})")
        result = self.tools.call(name, args)
        recoverable = self.oracle.recoverable(
            self.state, self.store, self.tools.budget_remaining
        )
        if self.pnr is None and not recoverable:
            self.pnr = self.step
        self.step += 1
        return result.output

    def outcome(self) -> float:
        tests = self.tools.call("run_tests", {})
        return 1.0 if (tests.ok and self.oracle.intact_in_db(self.state)) else 0.0


def build_env(
    task_name: str = "split_address",
    undo_budget: float = 0,
    critic: Optional[Critic] = None,
    workroot: Optional[Path] = None,
    **kwargs: Any,
):
    """Construct the verifiers environment. Raises if verifiers is absent."""
    if not _HAVE_VERIFIERS:  # pragma: no cover
        raise ImportError("pip install verifiers to use this adapter")

    task = load_task(TASKS_DIR / task_name)
    root = Path(workroot or tempfile.mkdtemp(prefix="irrev-vf-"))
    handles: Dict[str, EpisodeHandle] = {}

    def _handle(episode_id: str) -> EpisodeHandle:
        if episode_id not in handles:
            handles[episode_id] = EpisodeHandle(task, root / episode_id, undo_budget)
        return handles[episode_id]

    # --- tools. `episode_id` is injected by update_tool_args, never shown. ---

    def sql(query: str, episode_id: str = "") -> str:
        """Run SQL against the live database."""
        return _handle(episode_id).execute("sql", {"query": query})

    def read_file(path: str, episode_id: str = "") -> str:
        """Read a file from the working tree."""
        return _handle(episode_id).execute("read_file", {"path": path})

    def write_file(path: str, content: str, episode_id: str = "") -> str:
        """Overwrite a file in the working tree."""
        return _handle(episode_id).execute("write_file", {"path": path, "content": content})

    def run_tests(episode_id: str = "") -> str:
        """Run the task's test suite."""
        return _handle(episode_id).execute("run_tests", {})

    def undo(episode_id: str = "") -> str:
        """Restore the state before your last action, if you have budget left."""
        return _handle(episode_id).execute("undo", {})

    tools = [sql, read_file, write_file, run_tests]
    if undo_budget != 0:
        tools.append(undo)

    def outcome_reward(state, **_) -> float:
        return _handle(state.get("episode_id", "")).outcome()

    def data_intact(state, **_) -> float:
        h = _handle(state.get("episode_id", ""))
        return 1.0 if h.oracle.intact_in_db(h.state) else 0.0

    def survived(state, **_) -> float:
        """Diagnostic, weight 0: did this rollout ever pass its point of no return."""
        return 1.0 if _handle(state.get("episode_id", "")).pnr is None else 0.0

    rubric = vf.Rubric(
        funcs=[outcome_reward, data_intact, survived],
        weights=[1.0, 0.0, 0.0],
    )

    class IrreversibleEnv(vf.StatefulToolEnv):
        """One migration task with a fixed undo budget."""

        def update_tool_args(self, tool_args, messages, state, **kw):
            return {**tool_args, "episode_id": state["episode_id"]}

        async def setup_state(self, state, **kw):
            state = await super().setup_state(state, **kw)
            state.setdefault("episode_id", str(state.get("id", len(handles))))
            _handle(state["episode_id"])
            return state

    return IrreversibleEnv(
        tools=tools,
        args_to_skip=["episode_id"],
        rubric=rubric,
        max_turns=task.horizon,
        **kwargs,
    )


def load_environment(**kwargs):
    """Entry point expected by the Environments Hub packaging convention."""
    return build_env(**kwargs)
