"""Snapshot store — the mechanism behind the undo budget K.

A snapshot is taken immediately *before* every agent action, so ``undo``
restores the state the last action was taken from. The budget K is enforced
by the toolbox, not here; this class only knows how to save and restore.

The tree is always copied; the database artefact comes from the backend, so
this class is identical for SQLite (a file copy) and Postgres (a pg_dump).
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .state import EnvState


@dataclass(frozen=True)
class Snapshot:
    sid: str
    label: str
    path: Path

    @property
    def repo(self) -> Path:
        return self.path / "repo"

    @property
    def db(self) -> Path:
        """Directory holding this snapshot's database artefact."""
        return self.path


class SnapshotStore:
    def __init__(self, state: EnvState):
        self.state = state
        self.stack: List[Snapshot] = []
        self._n = 0
        state.snapdir.mkdir(parents=True, exist_ok=True)

    def take(self, label: str = "") -> Snapshot:
        sid = f"{self._n:04d}"
        self._n += 1
        path = self.state.snapdir / sid
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
        shutil.copytree(self.state.repo, path / "repo")
        self.state.database.dump(path)
        snap = Snapshot(sid, label, path)
        self.stack.append(snap)
        return snap

    def restore_last(self) -> Snapshot:
        """Pop the most recent snapshot and restore the live state from it."""
        if not self.stack:
            raise RuntimeError("no snapshot to restore")
        snap = self.stack.pop()
        if self.state.repo.exists():
            shutil.rmtree(self.state.repo)
        shutil.copytree(snap.repo, self.state.repo)
        self.state.database.load(snap.path)
        return snap

    def reachable(self, budget: float) -> List[Snapshot]:
        """Snapshots the agent could still restore, most recent first.

        With ``budget`` undos remaining the agent can walk back at most that
        many steps. This is what couples the recoverability oracle to K.
        """
        if budget == math.inf:
            return list(reversed(self.stack))
        n = int(max(0, budget))
        return list(reversed(self.stack[len(self.stack) - n:])) if n else []

    def __len__(self) -> int:
        return len(self.stack)
