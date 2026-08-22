"""Episode state: the three paths everything else operates on."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .db import Database, SqliteDatabase


@dataclass
class EnvState:
    """One episode's working directory.

    Layout::

        root/
          repo/          the agent's working tree (tools are confined here)
          db.sqlite      the live database
          .snapshots/    snapshot store — outside the agent's reach

    The separation matters: an agent that can read or write ``.snapshots``
    can manufacture recoverability, which would make the oracle a lie.
    """

    root: Path
    database: Optional[Database] = None

    def __post_init__(self):
        if self.database is None:
            self.database = SqliteDatabase(self.root / "db.sqlite")

    @property
    def repo(self) -> Path:
        return self.root / "repo"

    @property
    def db(self) -> Path:
        """SQLite backend only: the database file. Prefer ``database``."""
        return self.root / "db.sqlite"

    @property
    def snapdir(self) -> Path:
        return self.root / ".snapshots"

    def ensure(self) -> "EnvState":
        self.root.mkdir(parents=True, exist_ok=True)
        self.repo.mkdir(exist_ok=True)
        self.snapdir.mkdir(exist_ok=True)
        return self
