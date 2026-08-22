"""Tiny backend shim for task code — SQLite or Postgres, no driver required.

Copied into every task repo. The agent can read and edit it like any other
file; it is part of the working tree, not the harness.

Postgres access shells out to ``psql`` rather than depending on psycopg, so a
task image needs only the Postgres client tools. Parameters are substituted
client-side with proper quoting; the values here come from the database
itself, never from the agent.

Schema questions (which tables, which columns, which unique indexes) are the
only genuinely non-portable part, so they live behind three functions instead
of being spelled as ``PRAGMA`` in each task's verify.py.
"""

import os
import subprocess

SEP = "\x1f"


def _quote(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def _bind(sql, params):
    """Substitute ``?`` placeholders. Params are database values, not input."""
    out, rest = [], sql
    for value in params:
        head, sep, rest = rest.partition("?")
        if not sep:
            raise ValueError("more parameters than placeholders")
        out.append(head)
        out.append(_quote(value))
    out.append(rest)
    return "".join(out)


class SqliteConn:
    backend = "sqlite"

    def __init__(self, path):
        import sqlite3

        self._conn = sqlite3.connect(path)

    def execute(self, sql, params=()):
        return list(self._conn.execute(sql, params))

    def close(self):
        self._conn.close()


class PsqlConn:
    backend = "postgres"

    def __init__(self, dsn):
        self.dsn = dsn

    def execute(self, sql, params=()):
        if params:
            sql = _bind(sql, params)
        proc = subprocess.run(
            ["psql", self.dsn, "-v", "ON_ERROR_STOP=1", "-tA", "-F", SEP, "-c", sql],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout).strip()[-800:])
        rows = []
        for line in proc.stdout.splitlines():
            if line == "":
                continue
            rows.append(tuple(None if v == "" else v for v in line.split(SEP)))
        return rows

    def close(self):
        pass


def connect():
    dsn = os.environ.get("TASK_DSN")
    if dsn:
        return PsqlConn(dsn)
    path = os.environ.get("TASK_DB")
    if not path:
        raise RuntimeError("neither TASK_DSN nor TASK_DB is set")
    return SqliteConn(path)


# ---------- the non-portable questions, answered per backend ----------


def tables(conn):
    if conn.backend == "postgres":
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    else:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {r[0] for r in rows}


def columns(conn, table):
    if conn.backend == "postgres":
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?", (table,)
        )
        return {r[0] for r in rows}
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def has_unique_index(conn, table):
    if conn.backend == "postgres":
        rows = conn.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = ? "
            "AND indexdef LIKE '%UNIQUE%'",
            (table,),
        )
        return bool(rows)
    return any(int(r[2]) == 1 for r in conn.execute(f"PRAGMA index_list({table})"))


def one(conn, sql, params=()):
    rows = conn.execute(sql, params)
    return rows[0][0] if rows else None


def as_int(value, default=0):
    return default if value is None else int(value)
