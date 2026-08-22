"""Stdlib unittest suite — no third-party dependencies.

    python -m unittest discover -s irreversible/tests -t irreversible -v
"""

from __future__ import annotations

import math
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from irrev import (  # noqa: E402
    DESTRUCTIVE_PLAN,
    SAFE_PLAN,
    DataPairOracle,
    HazardAgent,
    OracleCritic,
    RandomCritic,
    ScriptedAgent,
    SnapshotStore,
    Toolbox,
    action_boundaries,
    assemble_rewards,
    load_task,
    loss_mask,
    naive_shaping,
    parse_turn,
    potential_shaping,
    render_action,
    run_episode,
    setup_episode,
)
from irrev.critics import CachingCritic, ConstantCritic  # noqa: E402
from irrev.shaping import discounted_return, shaping_is_policy_invariant  # noqa: E402
from sim.hazard_model import advantage_curve, binom_cdf, success  # noqa: E402

TASK_DIR = ROOT / "tasks" / "split_address"


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="irrev-test-"))
        self.task = load_task(TASK_DIR)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fresh(self, name="ep"):
        state, oracle = setup_episode(self.task, self.tmp / name)
        return state, oracle, SnapshotStore(state)


# ---------------------------------------------------------------- protocol


class TestProtocol(unittest.TestCase):
    def test_round_trip(self):
        turn = render_action("sql", {"query": "SELECT 1"}, "have a look")
        thought, name, args = parse_turn(turn)
        self.assertEqual(thought, "have a look")
        self.assertEqual(name, "sql")
        self.assertEqual(args, {"query": "SELECT 1"})

    def test_no_action(self):
        self.assertEqual(parse_turn("<thought>thinking</thought>")[1], None)

    def test_action_boundaries_are_scoring_points(self):
        text = render_action("sql", {"query": "a"}) + "<observation>ok</observation>" + render_action(
            "submit", {}
        )
        bounds = action_boundaries(text)
        self.assertEqual(len(bounds), 2)
        self.assertTrue(all(text[:b].endswith("</action>") for b in bounds))

    def test_observations_are_masked_out(self):
        text = "<thought>t</thought><observation>env said this</observation>"
        mask = loss_mask(text)
        start = text.index("<observation>")
        self.assertEqual(set(mask[:start]), {1})
        self.assertEqual(set(mask[start:]), {0})


# ---------------------------------------------------------------- shaping


class TestShaping(unittest.TestCase):
    def test_potential_shaping_telescopes(self):
        phi = [0.1, 0.4, 0.35, 0.9]
        self.assertAlmostEqual(sum(potential_shaping(phi, 1.0)), phi[-1] - phi[0])

    def test_policy_invariance_identity_discounted(self):
        phi = [0.2, 0.5, 0.1, 0.8, 0.4]
        for gamma in (1.0, 0.99, 0.9, 0.5):
            self.assertTrue(shaping_is_policy_invariant(phi, gamma), gamma)

    def test_shaping_cannot_change_relative_return_of_two_policies(self):
        # Two trajectories with the same start and end potential: shaping adds
        # exactly the same constant to both, so their ordering is preserved.
        a = [0.3, 0.9, 0.2, 0.7]
        b = [0.3, 0.1, 0.6, 0.7]
        ra = discounted_return(potential_shaping(a, 1.0))
        rb = discounted_return(potential_shaping(b, 1.0))
        self.assertAlmostEqual(ra, rb)

    def test_naive_shaping_does_not_telescope(self):
        phi = [0.1, 0.9, 0.9, 0.9]
        self.assertNotAlmostEqual(sum(naive_shaping(phi)), phi[-1] - phi[0])

    def test_assemble_puts_outcome_on_the_last_step(self):
        rewards = assemble_rewards(1.0, [0.0, 0.5, 1.0], gamma=1.0)
        self.assertEqual(len(rewards), 2)
        self.assertAlmostEqual(rewards[0], 0.5)
        self.assertAlmostEqual(rewards[1], 1.5)

    def test_mode_none_is_pure_outcome(self):
        rewards = assemble_rewards(1.0, [0.0, 0.9, 0.9], mode="none")
        self.assertEqual(rewards, [0.0, 1.0])


# ---------------------------------------------------------------- snapshots


class TestSnapshots(TempCase):
    def test_restore_brings_back_dropped_data(self):
        state, oracle, store = self.fresh()
        self.assertTrue(oracle.intact_in_db(state))
        store.take("before drop")
        conn = sqlite3.connect(state.db)
        conn.executescript("ALTER TABLE users DROP COLUMN address;")
        conn.commit()
        conn.close()
        self.assertFalse(oracle.intact_in_db(state))
        store.restore_last()
        self.assertTrue(oracle.intact_in_db(state))

    def test_reachable_is_bounded_by_budget(self):
        state, _, store = self.fresh()
        for i in range(5):
            store.take(f"s{i}")
        self.assertEqual(len(store.reachable(0)), 0)
        self.assertEqual(len(store.reachable(2)), 2)
        self.assertEqual(len(store.reachable(math.inf)), 5)
        self.assertEqual(store.reachable(2)[0].label, "s4")  # most recent first


# ---------------------------------------------------------------- oracle


class TestOracle(TempCase):
    def test_intact_before_anything_happens(self):
        state, oracle, _ = self.fresh()
        self.assertTrue(oracle.intact_now(state))
        self.assertAlmostEqual(oracle.fraction_now(state), 1.0)

    def test_migration_preserves_the_pairs(self):
        state, oracle, _ = self.fresh()
        conn = sqlite3.connect(state.db)
        conn.executescript(
            "CREATE TABLE addresses (id INTEGER PRIMARY KEY, user_id INTEGER, line TEXT);"
            "INSERT INTO addresses (user_id, line) SELECT id, address FROM users;"
            "ALTER TABLE users DROP COLUMN address;"
        )
        conn.commit()
        conn.close()
        self.assertTrue(oracle.intact_in_db(state))

    def test_destructive_drop_loses_the_pairs(self):
        state, oracle, _ = self.fresh()
        conn = sqlite3.connect(state.db)
        conn.executescript("ALTER TABLE users DROP COLUMN address;")
        conn.commit()
        conn.close()
        self.assertFalse(oracle.intact_in_db(state))
        self.assertAlmostEqual(oracle.fraction_now(state), 0.0)

    def test_a_file_dump_counts_as_recoverable_but_not_as_migrated(self):
        state, oracle, store = self.fresh()
        conn = sqlite3.connect(state.db)
        rows = conn.execute("SELECT id, address FROM users").fetchall()
        (state.repo / "backup.csv").write_text(
            "\n".join(f"{uid},{addr}" for uid, addr in rows)
        )
        conn.executescript("ALTER TABLE users DROP COLUMN address;")
        conn.commit()
        conn.close()
        self.assertTrue(oracle.intact_now(state))          # derivable from disk
        self.assertFalse(oracle.intact_in_db(state))       # but not migrated
        self.assertTrue(oracle.recoverable(state, store, 0))

    def test_recoverability_depends_on_the_undo_budget(self):
        state, oracle, store = self.fresh()
        store.take("pre-drop")
        conn = sqlite3.connect(state.db)
        conn.executescript("ALTER TABLE users DROP COLUMN address;")
        conn.commit()
        conn.close()
        self.assertFalse(oracle.recoverable(state, store, 0))   # irreversible
        self.assertTrue(oracle.recoverable(state, store, 1))    # one undo saves it
        self.assertTrue(oracle.recoverable(state, store, math.inf))

    def test_key_matching_is_token_exact(self):
        oracle = DataPairOracle([("1", "12 Wilton Crescent, London")])
        repo = self.tmp / "files"
        repo.mkdir(parents=True)
        (repo / "a.txt").write_text("user 17 lives at 12 Wilton Crescent, London\n")
        self.assertEqual(oracle.derivable(repo, None), set())
        (repo / "b.txt").write_text("user 1 lives at 12 Wilton Crescent, London\n")
        self.assertEqual(len(oracle.derivable(repo, None)), 1)


# ---------------------------------------------------------------- tools


class TestTools(TempCase):
    def test_undo_budget_is_enforced(self):
        state, _, store = self.fresh()
        tools = Toolbox(state, store, undo_budget=1)
        store.take("a")
        store.take("b")
        self.assertTrue(tools.call("undo", {}).ok)
        result = tools.call("undo", {})
        self.assertFalse(result.ok)
        self.assertIn("irreversible", result.output)

    def test_zero_budget_refuses_immediately(self):
        state, _, store = self.fresh()
        tools = Toolbox(state, store, undo_budget=0)
        store.take("a")
        self.assertFalse(tools.call("undo", {}).ok)

    def test_paths_cannot_escape_the_working_tree(self):
        state, _, store = self.fresh()
        tools = Toolbox(state, store)
        result = tools.call("write_file", {"path": "../../escape.txt", "content": "x"})
        self.assertFalse(result.ok)
        self.assertIn("escapes", result.output)

    def test_snapshot_store_is_not_reachable_from_tools(self):
        state, _, store = self.fresh()
        tools = Toolbox(state, store)
        listing = tools.call("list_files", {})
        self.assertNotIn(".snapshots", listing.output)

    def test_unknown_tool_is_reported_not_raised(self):
        state, _, store = self.fresh()
        result = Toolbox(state, store).call("rm_rf", {})
        self.assertFalse(result.ok)
        self.assertIn("unknown tool", result.output)

    def test_tests_fail_before_migration(self):
        state, _, store = self.fresh()
        self.assertFalse(Toolbox(state, store).call("run_tests", {}).ok)


# ---------------------------------------------------------------- episodes


class TestEpisodes(TempCase):
    def test_safe_plan_succeeds_with_no_undo_budget(self):
        traj = run_episode(self.task, ScriptedAgent(SAFE_PLAN), self.tmp / "safe", undo_budget=0)
        self.assertTrue(traj.tests_ok, traj.detail)
        self.assertTrue(traj.integrity_ok)
        self.assertIsNone(traj.pnr)
        self.assertTrue(all(s.recoverable for s in traj.steps))

    def test_destructive_plan_dies_at_the_drop(self):
        traj = run_episode(
            self.task, ScriptedAgent(DESTRUCTIVE_PLAN), self.tmp / "bad", undo_budget=0
        )
        self.assertFalse(traj.success)
        self.assertEqual(traj.pnr, 1)  # step 2, the DROP
        self.assertEqual(traj.steps[1].action, "sql")
        # every later step is generated from an unwinnable state
        self.assertTrue(all(not s.recoverable for s in traj.steps[1:]))

    def test_undo_budget_moves_the_point_of_no_return(self):
        # One undo buys exactly one step of grace: at the drop the pre-drop
        # snapshot is still reachable, but after the next action it has fallen
        # out of budget. The point of no return moves later by one step — it
        # does not disappear, because this agent never spends the undo.
        traj = run_episode(
            self.task, ScriptedAgent(DESTRUCTIVE_PLAN), self.tmp / "bad2", undo_budget=1
        )
        self.assertEqual(traj.pnr, 2)
        self.assertTrue(traj.steps[1].recoverable)

    def test_infinite_budget_removes_the_point_of_no_return(self):
        traj = run_episode(
            self.task, ScriptedAgent(DESTRUCTIVE_PLAN), self.tmp / "bad3", undo_budget=math.inf
        )
        self.assertIsNone(traj.pnr)
        self.assertTrue(all(s.recoverable for s in traj.steps))

    def test_hazard_agent_recovers_when_it_has_budget(self):
        agent = HazardAgent(hazard=1.0, seed=0)  # hazard on every eligible step
        traj = run_episode(
            self.task, agent, self.tmp / "haz", undo_budget=math.inf, max_steps=40
        )
        self.assertGreater(agent.hazards_hit, 0)
        self.assertGreater(traj.undo_used, 0)
        self.assertIsNone(traj.pnr)

    def test_hazard_agent_dies_without_budget(self):
        agent = HazardAgent(hazard=1.0, seed=0)
        traj = run_episode(self.task, agent, self.tmp / "haz0", undo_budget=0, max_steps=20)
        self.assertFalse(traj.success)
        self.assertIsNotNone(traj.pnr)

    def test_critic_produces_one_potential_per_boundary_plus_one(self):
        state_free_task = self.task
        traj = run_episode(
            state_free_task,
            ScriptedAgent(SAFE_PLAN),
            self.tmp / "phi",
            undo_budget=0,
            critic=ConstantCritic(0.5),
        )
        self.assertEqual(len(traj.phi), len(traj.steps) + 1)
        self.assertEqual(len(traj.rewards), len(traj.steps))

    def test_oracle_critic_potential_collapses_on_data_loss(self):
        traj = run_episode(
            self.task,
            ScriptedAgent(DESTRUCTIVE_PLAN),
            self.tmp / "phi2",
            undo_budget=0,
            critic=OracleCritic(DataPairOracle(self.task.protected_pairs)),
        )
        self.assertAlmostEqual(traj.phi[0], 1.0)
        self.assertAlmostEqual(traj.phi[-1], 0.0)
        # the shaping reward is sharply negative exactly at the fatal step
        self.assertLess(traj.rewards[1], -0.5)

    def test_caching_critic_deduplicates_prefixes(self):
        log = self.tmp / "labels.jsonl"
        critic = CachingCritic(ConstantCritic(0.4), log_path=log)
        for i in range(2):
            run_episode(
                self.task,
                ScriptedAgent(SAFE_PLAN),
                self.tmp / f"cache{i}",
                undo_budget=0,
                critic=critic,
            )
        self.assertGreater(critic.hits, 0)
        self.assertGreater(critic.hit_rate, 0.4)
        self.assertTrue(log.exists())

    def test_random_critic_is_a_deterministic_function_of_the_prefix(self):
        critic = RandomCritic(seed=7)
        a = critic.score(None, ["x", "y"])
        b = critic.score(None, ["x", "y"])
        c = critic.score(None, ["x", "z"])
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


# ---------------------------------------------------------------- model


class TestHazardModel(unittest.TestCase):
    def test_binom_cdf_edges(self):
        self.assertAlmostEqual(binom_cdf(5, 0.3, 5), 1.0)
        self.assertAlmostEqual(binom_cdf(5, 0.0, 0), 1.0)
        self.assertAlmostEqual(binom_cdf(3, 0.5, 0), 0.125)
        self.assertAlmostEqual(binom_cdf(3, 0.5, 1), 0.5)

    def test_advantage_is_largest_at_zero_and_decays(self):
        rows = advantage_curve()
        advantages = [r["advantage"] for r in rows]
        self.assertEqual(advantages[0], max(advantages))
        self.assertTrue(all(advantages[i] >= advantages[i + 1] - 1e-12
                            for i in range(len(advantages) - 1)))
        self.assertLess(advantages[-1], 0.01)

    def test_no_hazard_means_no_advantage(self):
        rows = advantage_curve(hazard=0.0)
        self.assertTrue(all(abs(r["advantage"]) < 1e-12 for r in rows))

    def test_matches_the_numbers_shown_in_the_explainer(self):
        # defaults of the interactive: H=12, h=0.10, r=0.45, base=0.70
        rows = advantage_curve(horizon=12, hazard=0.10, reduction=0.45, base=0.70)
        self.assertAlmostEqual(rows[0]["advantage"] * 100, 15.7, places=1)
        self.assertAlmostEqual(rows[2]["advantage"] * 100, 6.0, places=1)

    def test_success_saturates_at_base(self):
        self.assertAlmostEqual(success(8, 0.2, 8, base=0.7), 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
