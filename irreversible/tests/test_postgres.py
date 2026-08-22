"""Postgres backend, against a real cluster.

Skipped unless one is reachable. To run one locally without Docker:

    PGDATA=/var/lib/postgresql/irrev PGBIN=/usr/lib/postgresql/16/bin
    su postgres -c "$PGBIN/initdb -D $PGDATA -A trust -U postgres"
    su postgres -c "$PGBIN/pg_ctl -D $PGDATA -o '-p 55432 -k /tmp' start"
    IRREV_PG_PORT=55432 python -m unittest discover -s tests -t .

These are the tests that matter for the container path, because the Postgres
backend differs from SQLite in exactly one structural way: a snapshot is a
dump, not a queryable database. Asking "were the pairs derivable from that
earlier state?" means restoring it into a scratch database first — and that is
the operation the whole point-of-no-return measurement rests on.
"""

from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from irrev import PLANS, ScriptedAgent, SnapshotStore, Toolbox, load_task, run_episode, setup_episode  # noqa: E402
from irrev.db import PostgresDatabase  # noqa: E402

TASKS_DIR = ROOT / "tasks"

PG_HOST = os.environ.get("IRREV_PG_HOST", "/tmp")
PG_PORT = int(os.environ.get("IRREV_PG_PORT", "0") or 0)
PG_USER = os.environ.get("IRREV_PG_USER", "postgres")
PG_BINDIR = os.environ.get("IRREV_PG_BINDIR", "/usr/lib/postgresql/16/bin")


def _reachable() -> bool:
    if not PG_PORT:
        return False
    probe = PostgresDatabase("postgres", PG_HOST, PG_PORT, PG_USER, bindir=PG_BINDIR)
    return probe.exists()


REACHABLE = _reachable()


@unittest.skipUnless(REACHABLE, "no Postgres cluster (set IRREV_PG_PORT)")
class PostgresCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="irrev-pg-"))
        self.dbs = []

    def tearDown(self):
        for db in self.dbs:
            try:
                db.drop()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def database(self) -> PostgresDatabase:
        db = PostgresDatabase(
            f"irrev_{uuid.uuid4().hex[:10]}", PG_HOST, PG_PORT, PG_USER, bindir=PG_BINDIR
        )
        self.dbs.append(db)
        return db

    def episode(self, task_name="split_address"):
        task = load_task(TASKS_DIR / task_name)
        state, oracle = setup_episode(task, self.tmp / task_name, database=self.database())
        return task, state, oracle


class TestPostgresBackend(PostgresCase):
    def test_seed_and_protected_pairs_match_sqlite(self):
        task, state, oracle = self.episode()
        sqlite_task = load_task(TASKS_DIR / "split_address")
        self.assertEqual(set(task.protected_pairs), set(sqlite_task.protected_pairs))
        self.assertTrue(oracle.intact_in_db(state))

    def test_dump_and_restore_round_trip(self):
        task, state, oracle = self.episode()
        store = SnapshotStore(state)
        store.take("before drop")
        state.database.execute("ALTER TABLE users DROP COLUMN address;")
        self.assertFalse(oracle.intact_in_db(state))
        store.restore_last()
        self.assertTrue(oracle.intact_in_db(state))

    def test_snapshot_view_restores_into_a_scratch_database_and_drops_it(self):
        task, state, oracle = self.episode()
        store = SnapshotStore(state)
        snap = store.take("s0")
        state.database.execute("ALTER TABLE users DROP COLUMN address;")

        with state.database.snapshot_view(snap.path) as view:
            self.assertIsNotNone(view)
            scratch_name = view.dbname
            self.assertNotEqual(scratch_name, state.database.dbname)
            self.assertTrue(oracle.derivable(snap.repo, view) >= oracle.pairs)

        leaked = PostgresDatabase(scratch_name, PG_HOST, PG_PORT, PG_USER, bindir=PG_BINDIR)
        self.assertFalse(leaked.exists(), "scratch database was not dropped")

    def test_recoverability_still_depends_on_the_undo_budget(self):
        task, state, oracle = self.episode()
        store = SnapshotStore(state)
        store.take("pre-drop")
        state.database.execute("ALTER TABLE users DROP COLUMN address;")
        self.assertFalse(oracle.recoverable(state, store, 0))
        self.assertTrue(oracle.recoverable(state, store, 1))
        self.assertTrue(oracle.recoverable(state, store, math.inf))

    def test_undo_through_the_tool_surface(self):
        task, state, oracle = self.episode()
        store = SnapshotStore(state)
        tools = Toolbox(state, store, undo_budget=1)
        store.take("pre-drop")
        tools.call("sql", {"query": "ALTER TABLE users DROP COLUMN address;"})
        self.assertFalse(oracle.intact_in_db(state))
        result = tools.call("undo", {})
        self.assertTrue(result.ok, result.output)
        self.assertTrue(oracle.intact_in_db(state))

    def test_the_sql_tool_reads_and_writes(self):
        task, state, oracle = self.episode()
        tools = Toolbox(state, SnapshotStore(state))
        read = tools.call("sql", {"query": "SELECT count(*) FROM users"})
        self.assertTrue(read.ok, read.output)
        self.assertIn("12", read.output)
        self.assertTrue(tools.call("sql", {"query": "CREATE TABLE t (x INTEGER);"}).ok)
        self.assertIn("t", state.database.tables())


class TestPostgresEpisodes(PostgresCase):
    """The full loop, including the task's own verify.py through taskdb."""

    def run_plan(self, task_name, which, undo_budget=0):
        task = load_task(TASKS_DIR / task_name)
        plan = getattr(PLANS[task_name], which)
        return run_episode(
            task,
            ScriptedAgent(plan),
            self.tmp / f"{task_name}-{which}",
            undo_budget=undo_budget,
            database=self.database(),
        )

    def test_safe_plans_succeed_on_postgres(self):
        for name in PLANS:
            with self.subTest(task=name):
                traj = self.run_plan(name, "safe")
                self.assertTrue(traj.tests_ok, f"{name}: {traj.detail}")
                self.assertTrue(traj.integrity_ok, name)
                self.assertIsNone(traj.pnr, name)

    def test_destructive_plans_die_on_postgres(self):
        for name in PLANS:
            with self.subTest(task=name):
                traj = self.run_plan(name, "destructive")
                self.assertFalse(traj.success, name)
                self.assertEqual(traj.pnr, 1, name)

    def test_undo_budget_moves_the_point_of_no_return_on_postgres(self):
        traj = self.run_plan("split_address", "destructive", undo_budget=1)
        self.assertEqual(traj.pnr, 2)
        traj_inf = self.run_plan("split_address", "destructive", undo_budget=math.inf)
        self.assertIsNone(traj_inf.pnr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
