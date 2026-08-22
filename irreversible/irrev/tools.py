"""The agent's tool surface, and enforcement of the undo budget K."""

from __future__ import annotations

import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .db import is_read_only
from .snapshot import SnapshotStore
from .state import EnvState

TOOL_NAMES = ("sql", "read_file", "write_file", "list_files", "run_tests", "undo", "submit")


@dataclass
class ToolResult:
    ok: bool
    output: str
    submitted: bool = False


class Toolbox:
    """Confined tool surface.

    Deliberately no ``bash``. Arbitrary command execution is what the Docker
    backend is for; running it against the host from an exploring RL policy is
    not a risk worth taking for a local harness. Set ``allow_shell=True`` only
    inside a container.
    """

    def __init__(
        self,
        state: EnvState,
        store: SnapshotStore,
        undo_budget: float = 0,
        allow_shell: bool = False,
        test_timeout: int = 60,
    ):
        self.state = state
        self.store = store
        self.undo_budget = undo_budget
        self.undo_used = 0
        self.allow_shell = allow_shell
        self.test_timeout = test_timeout

    @property
    def budget_remaining(self) -> float:
        if self.undo_budget == math.inf:
            return math.inf
        return max(0.0, self.undo_budget - self.undo_used)

    # ---------- dispatch ----------

    def call(self, name: str, args: Dict[str, str]) -> ToolResult:
        fn = getattr(self, f"_t_{name}", None)
        if fn is None:
            return ToolResult(False, f"unknown tool {name!r}; available: {', '.join(TOOL_NAMES)}")
        try:
            return fn(**args)
        except TypeError as exc:
            return ToolResult(False, f"bad arguments for {name}: {exc}")
        except Exception as exc:  # tools report failure, they don't crash the episode
            return ToolResult(False, f"{type(exc).__name__}: {exc}")

    # ---------- individual tools ----------

    def _resolve(self, path: str) -> Path:
        target = (self.state.repo / path).resolve()
        repo = self.state.repo.resolve()
        if repo != target and repo not in target.parents:
            raise ValueError(f"path escapes the working tree: {path}")
        return target

    def _t_sql(self, query: str) -> ToolResult:
        db = self.state.database
        if is_read_only(query):
            cols, rows = db.read(query)
            body = "\n".join(" | ".join(str(v) for v in r) for r in rows[:50])
            more = f"\n... {len(rows) - 50} more rows" if len(rows) > 50 else ""
            return ToolResult(True, (" | ".join(cols) + "\n" + body + more).strip())
        db.execute(query)
        return ToolResult(True, "ok")

    def _t_read_file(self, path: str) -> ToolResult:
        p = self._resolve(path)
        if not p.is_file():
            return ToolResult(False, f"no such file: {path}")
        return ToolResult(True, p.read_text(errors="ignore"))

    def _t_write_file(self, path: str, content: str) -> ToolResult:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return ToolResult(True, f"wrote {len(content)} bytes to {path}")

    def _t_list_files(self) -> ToolResult:
        repo = self.state.repo
        names = sorted(
            str(p.relative_to(repo))
            for p in repo.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
        return ToolResult(True, "\n".join(names))

    def _t_run_tests(self) -> ToolResult:
        env = dict(os.environ, **self.state.database.env())
        try:
            proc = subprocess.run(
                [sys.executable, "verify.py"],
                cwd=self.state.repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.test_timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(False, "verify.py timed out")
        out = (proc.stdout + proc.stderr).strip()
        return ToolResult(proc.returncode == 0, out[-4000:])

    def _t_undo(self) -> ToolResult:
        if self.budget_remaining <= 0:
            return ToolResult(False, "no undo budget remaining — this environment is irreversible")
        if len(self.store) == 0:
            return ToolResult(False, "nothing to undo")
        snap = self.store.restore_last()
        self.undo_used += 1
        left = self.budget_remaining
        left_s = "unlimited" if left == math.inf else str(int(left))
        return ToolResult(True, f"restored state before {snap.label or snap.sid}; undos left: {left_s}")

    def _t_submit(self) -> ToolResult:
        return ToolResult(True, "submitted", submitted=True)
