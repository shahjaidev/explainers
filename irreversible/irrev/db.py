"""Database backends.

The harness needs four things from a database, and both backends provide them
the same way:

* run a statement, read a query — the ``sql`` tool and the oracle;
* dump and load — the snapshot store;
* open a *snapshot* as a queryable database — the recoverability oracle, which
  has to ask "were the protected pairs derivable from this earlier state?".

That last one is why this abstraction exists. For SQLite a snapshot is a file
and opening it is free. For Postgres a snapshot is a dump, and answering the
question means restoring it into a scratch database, asking, and dropping it.
Expensive — but the oracle only reaches for snapshots once the live state has
already lost the data, which is rare, and correctness here is the whole point
of the study.

The Postgres backend shells out to ``psql``/``pg_dump``/``pg_restore`` rather
than taking a driver dependency, so the harness stays stdlib-only.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Protocol, Sequence, Tuple
from urllib.parse import quote

Row = Tuple


class Database(Protocol):
    def exists(self) -> bool: ...
    def reset(self) -> None: ...
    def execute(self, sql: str) -> None: ...
    def read(self, sql: str) -> Tuple[List[str], List[Row]]: ...
    def tables(self) -> List[str]: ...
    def dump(self, dest: Path) -> None: ...
    def load(self, src: Path) -> None: ...
    def env(self) -> Dict[str, str]: ...
    @contextmanager
    def snapshot_view(self, src: Path) -> Iterator[Optional["Database"]]: ...


def is_read_only(sql: str) -> bool:
    head = sql.strip().lstrip("(").split(None, 1)
    return bool(head) and head[0].lower() in ("select", "pragma", "with", "explain", "show")


# --------------------------------------------------------------------------
# SQLite — the default. A snapshot is a copy of the file.
# --------------------------------------------------------------------------


class SqliteDatabase:
    kind = "sqlite"
    dump_name = "db.sqlite"

    def __init__(self, path: Path):
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        return sqlite3.connect(self.path)

    def execute(self, sql: str) -> None:
        conn = self._connect()
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    def read(self, sql: str) -> Tuple[List[str], List[Row]]:
        conn = self._connect(read_only=self.exists())
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return cols, rows
        finally:
            conn.close()

    def tables(self) -> List[str]:
        _, rows = self.read(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') "
            "AND name NOT LIKE 'sqlite_%'"
        )
        return [r[0] for r in rows]

    def dump(self, dest: Path) -> None:
        if self.exists():
            shutil.copy2(self.path, Path(dest) / self.dump_name)

    def load(self, src: Path) -> None:
        artefact = Path(src) / self.dump_name
        if artefact.exists():
            shutil.copy2(artefact, self.path)
        elif self.exists():
            self.path.unlink()

    def env(self) -> Dict[str, str]:
        return {"TASK_DB": str(self.path.resolve())}

    @contextmanager
    def snapshot_view(self, src: Path) -> Iterator[Optional["SqliteDatabase"]]:
        artefact = Path(src) / self.dump_name
        yield SqliteDatabase(artefact) if artefact.exists() else None


# --------------------------------------------------------------------------
# Postgres — the container path. A snapshot is a pg_dump.
# --------------------------------------------------------------------------


class PostgresError(RuntimeError):
    pass


class PostgresDatabase:
    kind = "postgres"
    dump_name = "db.dump"

    def __init__(
        self,
        dbname: str,
        host: str = "/tmp",
        port: int = 5432,
        user: str = "postgres",
        bindir: Optional[str] = None,
        timeout: int = 120,
    ):
        self.dbname = dbname
        self.host = host
        self.port = port
        self.user = user
        self.bindir = bindir or os.environ.get("PG_BINDIR", "")
        self.timeout = timeout

    # ---- process plumbing ----

    def _bin(self, name: str) -> str:
        return str(Path(self.bindir) / name) if self.bindir else name

    def _base_args(self, dbname: Optional[str] = None) -> List[str]:
        return [
            "-h", self.host,
            "-p", str(self.port),
            "-U", self.user,
            "-d", dbname or self.dbname,
        ]

    def _run(self, argv: Sequence[str], stdin: Optional[str] = None) -> str:
        proc = subprocess.run(
            list(argv),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=dict(os.environ, PGCONNECT_TIMEOUT="10"),
        )
        if proc.returncode != 0:
            raise PostgresError((proc.stderr or proc.stdout).strip()[-2000:])
        return proc.stdout

    def _psql(self, sql: str, dbname: Optional[str] = None, tuples_only: bool = False) -> str:
        argv = [self._bin("psql"), *self._base_args(dbname), "-v", "ON_ERROR_STOP=1"]
        if tuples_only:
            argv += ["-tA", "-F", "\x1f"]
        argv += ["-c", sql] if "\n" not in sql.strip() else ["-f", "-"]
        return self._run(argv, stdin=None if "-c" in argv else sql)

    # ---- Database protocol ----

    def exists(self) -> bool:
        try:
            out = self._run(
                [
                    self._bin("psql"), "-h", self.host, "-p", str(self.port),
                    "-U", self.user, "-d", "postgres", "-tA", "-c",
                    f"SELECT 1 FROM pg_database WHERE datname = '{self.dbname}'",
                ]
            )
        except (PostgresError, OSError, subprocess.SubprocessError):
            return False
        return out.strip() == "1"

    def create(self) -> None:
        self._run([self._bin("createdb"), "-h", self.host, "-p", str(self.port),
                   "-U", self.user, self.dbname])

    def drop(self) -> None:
        self._run([self._bin("dropdb"), "-h", self.host, "-p", str(self.port),
                   "-U", self.user, "--if-exists", "--force", self.dbname])

    def reset(self) -> None:
        self.drop()
        self.create()

    def execute(self, sql: str) -> None:
        self._psql(sql)

    def read(self, sql: str) -> Tuple[List[str], List[Row]]:
        out = self._run(
            [self._bin("psql"), *self._base_args(), "-v", "ON_ERROR_STOP=1",
             "-tA", "-F", "\x1f", "-c", sql]
        )
        rows = [tuple(line.split("\x1f")) for line in out.splitlines() if line != ""]
        return [], rows

    def tables(self) -> List[str]:
        _, rows = self.read(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        return [r[0] for r in rows]

    def dump(self, dest: Path) -> None:
        if not self.exists():
            return
        self._run([self._bin("pg_dump"), "-h", self.host, "-p", str(self.port),
                   "-U", self.user, "-Fc", "-f", str(Path(dest) / self.dump_name), self.dbname])

    def load(self, src: Path) -> None:
        artefact = Path(src) / self.dump_name
        if not artefact.exists():
            self.drop()
            return
        self.drop()
        self.create()
        self._run([self._bin("pg_restore"), "-h", self.host, "-p", str(self.port),
                   "-U", self.user, "-d", self.dbname, "--no-owner", str(artefact)])

    def env(self) -> Dict[str, str]:
        # A Unix socket directory cannot go in the host position of a URI —
        # psql reads "postgresql://postgres@/tmp:55432/db" as the database
        # "tmp:55432/db". The parameter form handles both socket and TCP.
        if self.host.startswith("/"):
            dsn = (
                f"postgresql:///{self.dbname}?host={quote(self.host, safe='')}"
                f"&port={self.port}&user={self.user}"
            )
        else:
            dsn = f"postgresql://{self.user}@{self.host}:{self.port}/{self.dbname}"
        return {
            "TASK_DSN": dsn,
            "PGHOST": self.host,
            "PGPORT": str(self.port),
            "PGUSER": self.user,
            "PGDATABASE": self.dbname,
        }

    @contextmanager
    def snapshot_view(self, src: Path) -> Iterator[Optional["PostgresDatabase"]]:
        """Restore a dump into a scratch database, hand it over, then drop it.

        The oracle needs to *query* an earlier state, and a pg_dump is not
        queryable. This is the expensive operation in the Postgres backend, and
        it only runs when the live state has already lost the protected data.
        """
        artefact = Path(src) / self.dump_name
        if not artefact.exists():
            yield None
            return
        scratch = PostgresDatabase(
            f"{self.dbname}_snap_{uuid.uuid4().hex[:10]}",
            host=self.host,
            port=self.port,
            user=self.user,
            bindir=self.bindir,
            timeout=self.timeout,
        )
        try:
            scratch.load(src)
            yield scratch
        finally:
            try:
                scratch.drop()
            except PostgresError:
                pass
