"""Task loading and episode setup.

A task is Harbor-shaped: a container recipe, an instruction, and a test. Here
the test is ``repo/verify.py`` (run by the ``run_tests`` tool) and the
container is optional — the local backend builds a SQLite database from
``seed.sql`` so the whole harness runs without Docker.

One thing the task holds that the agent never sees: the protected pairs,
extracted from the seed database *before* the agent touches anything. They
are the ground truth for both the integrity half of the outcome reward and
the recoverability oracle.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .oracle import DataPairOracle, Pair
from .state import EnvState


@dataclass
class Task:
    name: str
    directory: Path
    instruction: str
    horizon: int
    protected_query: str
    protected_pairs: List[Pair] = field(default_factory=list)

    @property
    def seed_sql(self) -> Path:
        return self.directory / "seed.sql"

    @property
    def repo_template(self) -> Path:
        return self.directory / "repo"


def load_task(directory: Path) -> Task:
    directory = Path(directory)
    spec = json.loads((directory / "task.json").read_text())
    task = Task(
        name=spec["name"],
        directory=directory,
        instruction=spec["instruction"].strip(),
        horizon=int(spec.get("horizon", 16)),
        protected_query=spec["protected_query"],
    )
    # Populate the protected pairs eagerly from the seed, so a critic or an
    # analysis script can be constructed before any episode exists. Without
    # this an oracle built from an unloaded task silently protects nothing.
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(task.seed_sql.read_text())
        task.protected_pairs = [(str(k), str(v)) for k, v in conn.execute(task.protected_query)]
    finally:
        conn.close()
    return task


def setup_episode(task: Task, root: Path) -> Tuple[EnvState, DataPairOracle]:
    """Materialise a fresh episode and compute its protected pairs."""
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
    state = EnvState(root)
    root.mkdir(parents=True)
    shutil.copytree(task.repo_template, state.repo)
    state.snapdir.mkdir()

    conn = sqlite3.connect(state.db)
    try:
        conn.executescript(task.seed_sql.read_text())
        conn.commit()
        pairs = [(str(k), str(v)) for k, v in conn.execute(task.protected_query)]
    finally:
        conn.close()

    task.protected_pairs = pairs
    return state, DataPairOracle(pairs)
