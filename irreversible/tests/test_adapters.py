"""Tests for the trainer-facing advantage path."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.prime_rl_shaping import (  # noqa: E402
    build_group_advantages,
    group_relative_advantages,
    token_advantages,
    turn_returns,
)


class TestGroupAdvantages(unittest.TestCase):
    def test_group_relative_is_zero_mean(self):
        adv = group_relative_advantages([1.0, 0.0, 0.0, 1.0])
        self.assertAlmostEqual(sum(adv), 0.0)

    def test_identical_returns_give_no_signal(self):
        self.assertEqual(group_relative_advantages([0.5, 0.5, 0.5]), [0.0, 0.0, 0.0])

    def test_near_zero_variance_does_not_amplify_float_noise(self):
        # Returns that agree to within float32 precision must give no signal.
        # Without the guard, dividing by (std + 1e-6) turns a 1e-8 difference
        # into a +-0.03 advantage — a gradient built entirely from rounding.
        adv = group_relative_advantages([1.5000000149, 1.5000000596])
        self.assertEqual(adv, [0.0, 0.0])

    def test_turn_returns_are_return_to_go(self):
        # potential shaping over phi, plus outcome on the last transition
        rets = turn_returns(1.0, [0.0, 0.5, 1.0], gamma=1.0)
        self.assertEqual(len(rets), 2)
        self.assertAlmostEqual(rets[1], 1.5)   # 1.0 shaping + 1.0 outcome - 0.5
        self.assertAlmostEqual(rets[0], 2.0)   # plus the first 0.5 of shaping

    def test_no_shaping_degenerates_to_outcome_grpo(self):
        rets = turn_returns(1.0, [0.3, 0.9, 0.2], mode="none")
        self.assertEqual(rets, [1.0, 1.0])

    def test_token_advantages_only_touch_action_spans(self):
        adv = token_advantages([2.0, -1.0], [(1, 3), (5, 7)], n_tokens=8)
        self.assertEqual(adv, [0.0, 2.0, 2.0, 0.0, 0.0, -1.0, -1.0, 0.0])

    def test_token_advantages_respect_the_loss_mask(self):
        mask = [1, 1, 0, 1, 1, 1, 1, 1]
        adv = token_advantages([2.0], [(1, 4)], n_tokens=8, trainable=mask)
        self.assertEqual(adv[2], 0.0)   # masked observation token
        self.assertEqual(adv[1], 2.0)

    def test_shaping_redistributes_credit_without_changing_the_total(self):
        # Two rollouts, same outcome and same start/end potential, but A makes
        # its progress on turn 1 and B on turn 2.
        group = [
            {"outcome": 1.0, "phi": [0.5, 0.9, 1.0], "token_spans": [(0, 1), (1, 2)], "n_tokens": 2},
            {"outcome": 1.0, "phi": [0.5, 0.1, 1.0], "token_spans": [(0, 1), (1, 2)], "n_tokens": 2},
        ]
        shaped = build_group_advantages(group, mode="potential")
        flat = build_group_advantages(group, mode="none")

        # Outcome-only cannot tell the two rollouts apart at any turn.
        self.assertEqual(flat[0], [0.0, 0.0])
        self.assertEqual(flat[1], [0.0, 0.0])

        # Neither can shaping, at turn 0: the return-to-go from the start is
        # phi[-1] - phi[0] + outcome for both. That is the policy-invariance
        # guarantee showing up in the advantages — shaping cannot change which
        # trajectory is preferred overall.
        self.assertAlmostEqual(shaped[0][0], shaped[1][0])

        # What it does change is *where inside a rollout* the credit lands.
        # At turn 1 the rollout that still had progress left to make carries
        # the larger advantage.
        self.assertGreater(shaped[1][1], shaped[0][1])

    def test_ragged_rollout_lengths(self):
        group = [
            {"outcome": 1.0, "phi": [0.0, 0.5, 1.0], "token_spans": [(0, 1), (1, 2)], "n_tokens": 3},
            {"outcome": 0.0, "phi": [0.0, 0.2], "token_spans": [(0, 1)], "n_tokens": 3},
        ]
        adv = build_group_advantages(group)
        self.assertEqual(len(adv), 2)
        self.assertEqual(len(adv[0]), 3)
        # turn index 1 exists in only one rollout, so it has no group baseline
        self.assertAlmostEqual(adv[0][1], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
