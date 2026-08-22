"""Integration tests against a real verifiers install (0.3.0).

Skipped when verifiers is absent, so the default suite stays dependency-free:

    python -m venv .venv && .venv/bin/pip install verifiers
    .venv/bin/python -m unittest discover -s tests -t .

These do not need a model. They exercise the contract that actually matters —
that the sandbox handle is hidden from the schema the agent sees and injected
at call time — by driving the tools directly.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.verifiers_env import STATE_KEY, EpisodeHandle, _HAVE_VERIFIERS, build_env  # noqa: E402
from irrev import PLANS  # noqa: E402


@unittest.skipUnless(_HAVE_VERIFIERS, "verifiers not installed")
class TestVerifiersAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="irrev-vf-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self, task="split_address", undo_budget=0):
        return build_env(
            task, undo_budget=undo_budget, workroot=self.tmp / task, dataset_size=2
        )

    # ---------- the injection contract ----------

    def test_handle_is_hidden_from_every_tool_schema(self):
        env = self.env()
        for tool_def in env.tool_defs:
            props = (tool_def.parameters or {}).get("properties", {})
            self.assertNotIn("handle", props, tool_def.name)
            self.assertNotIn("handle", (tool_def.parameters or {}).get("required", []))
        self.assertTrue(all(v == ["handle"] for v in env.skipped_args.values()))

    def test_agent_visible_args_survive(self):
        env = self.env()
        sql_def = next(t for t in env.tool_defs if t.name == "sql")
        self.assertIn("query", sql_def.parameters["properties"])
        self.assertEqual(sql_def.parameters["required"], ["query"])

    def test_setup_state_creates_one_handle_per_rollout(self):
        env = self.env()
        a = asyncio.run(env.setup_state({}))
        b = asyncio.run(env.setup_state({}))
        self.assertIsInstance(a[STATE_KEY], EpisodeHandle)
        self.assertIsNot(a[STATE_KEY], b[STATE_KEY])
        self.assertNotEqual(a[STATE_KEY].state.root, b[STATE_KEY].state.root)

    def test_update_tool_args_injects_the_handle(self):
        env = self.env()
        state = asyncio.run(env.setup_state({}))
        args = env.update_tool_args("sql", {"query": "SELECT 1"}, [], state)
        self.assertIs(args["handle"], state[STATE_KEY])
        self.assertEqual(args["query"], "SELECT 1")

    def test_a_tool_called_without_a_handle_fails_loudly(self):
        env = self.env()
        with self.assertRaises(RuntimeError):
            env.tool_map["sql"](query="SELECT 1")

    def test_undo_is_absent_when_the_budget_is_zero(self):
        self.assertNotIn("undo", [t.name for t in self.env(undo_budget=0).tool_defs])
        self.assertIn("undo", [t.name for t in self.env(undo_budget=2).tool_defs])

    # ---------- driving a real migration through the env ----------

    @staticmethod
    def _score(env, state):
        # The env wraps our Rubric in a RubricGroup alongside its own monitors.
        rubric = env.rubric.rubrics[0] if hasattr(env.rubric, "rubrics") else env.rubric
        return {f.__name__: f(state=state) for f in rubric.funcs}

    def _drive(self, env, plan):
        state = asyncio.run(env.setup_state({}))
        for _, name, args in plan:
            if name == "submit":
                break
            injected = env.update_tool_args(name, dict(args), [], state)
            env.tool_map[name](**injected)
        return state

    def test_safe_plan_scores_one(self):
        env = self.env()
        state = self._drive(env, PLANS["split_address"].safe)
        rewards = self._score(env, state)
        self.assertEqual(rewards["outcome_reward"], 1.0)
        self.assertEqual(rewards["data_intact"], 1.0)
        self.assertEqual(rewards["survived"], 1.0)

    def test_destructive_plan_scores_zero_and_records_the_death(self):
        env = self.env()
        state = self._drive(env, PLANS["split_address"].destructive)
        handle = state[STATE_KEY]
        rewards = self._score(env, state)
        self.assertEqual(rewards["outcome_reward"], 0.0)
        self.assertEqual(rewards["survived"], 0.0)
        self.assertEqual(handle.pnr, 1)

    def test_undo_restores_through_the_tool_surface(self):
        env = self.env(undo_budget=1)
        state = asyncio.run(env.setup_state({}))
        handle = state[STATE_KEY]
        drop = {"query": "ALTER TABLE users DROP COLUMN address;"}
        env.tool_map["sql"](**env.update_tool_args("sql", drop, [], state))
        self.assertFalse(handle.integrity_ok())
        out = env.tool_map["undo"](**env.update_tool_args("undo", {}, [], state))
        self.assertIn("restored", out)
        self.assertTrue(handle.integrity_ok())


if __name__ == "__main__":
    unittest.main(verbosity=2)
