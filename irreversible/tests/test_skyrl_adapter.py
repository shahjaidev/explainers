"""SkyRL advantage estimator — tensor contract and the two properties.

Needs torch, which the harness does not otherwise require, so these skip by
default:

    python3.12 -m venv .venv && .venv/bin/pip install torch
    .venv/bin/python -m unittest discover -s tests -t .

skyrl-train itself could not be installed in the environment this was written
in — its dependency `flash-attn` builds from source and needs `nvcc`, which
needs a CUDA toolkit. So the *signature* here is taken from skyrl-train 0.3.1's
source (`skyrl_train/utils/ppo_utils.py`) rather than from a live import, and
what these tests verify is that our estimator honours that contract and the two
mathematical properties the study depends on. `register()` is a no-op returning
False when SkyRL is absent, which is what these assert.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.skyrl_advantage import (  # noqa: E402
    ESTIMATOR_NAME,
    advantages_from_turns,
    compute_potential_shaped_advantage,
    register,
)

try:
    import numpy as np
    import torch

    HAVE_TORCH = True
except ImportError:  # pragma: no cover
    HAVE_TORCH = False


class TestPurePython(unittest.TestCase):
    """The arithmetic, with no tensors involved."""

    def test_group_is_zero_mean_at_every_turn(self):
        adv = advantages_from_turns([[0.0, 1.0], [0.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
                                    groups=[0, 0, 0, 0], norm_by_std=False)
        for t in range(2):
            self.assertAlmostEqual(sum(row[t] for row in adv), 0.0)

    def test_groups_do_not_leak_into_each_other(self):
        adv = advantages_from_turns([[1.0], [1.0], [0.0], [0.0]], groups=[0, 0, 1, 1])
        self.assertEqual(adv, [[0.0], [0.0], [0.0], [0.0]])  # each group is uniform

    def test_ragged_rollouts_use_only_the_members_that_got_there(self):
        adv = advantages_from_turns([[0.0, 0.0, 1.0], [0.0, 1.0]], groups=[0, 0],
                                    norm_by_std=False)
        # turn 2 exists in one rollout only, so it has no baseline to beat
        self.assertAlmostEqual(adv[0][2], 0.0)


@unittest.skipUnless(HAVE_TORCH, "torch not installed")
class TestSkyRLContract(unittest.TestCase):
    """Shapes, dtypes and return signature, per skyrl-train 0.3.1."""

    def call(self, rewards, mask=None, index=None, **kw):
        rewards = torch.tensor(rewards, dtype=torch.float32)
        if mask is None:
            mask = torch.ones_like(rewards)
        else:
            mask = torch.tensor(mask, dtype=torch.float32)
        if index is None:
            index = np.zeros(rewards.shape[0], dtype=object)
        return compute_potential_shaped_advantage(rewards, mask, index, **kw)

    def test_returns_two_tensors_of_the_input_shape_and_dtype(self):
        adv, ret = self.call([[0, 0, 1.0], [0, 0, 0.0]])
        for out in (adv, ret):
            self.assertEqual(out.shape, (2, 3))
            self.assertEqual(out.dtype, torch.float32)

    def test_masked_positions_stay_zero(self):
        adv, _ = self.call([[0, 0, 1.0], [0, 0, 0.0]], mask=[[1, 1, 0], [1, 1, 0]])
        self.assertTrue(torch.all(adv[:, 2] == 0))

    def test_reduces_to_grpo_outcome_advantage_without_shaping(self):
        # Rewards only at the final token: every rollout is one turn, so the
        # result must equal (score - group mean) / (group std + eps), broadcast
        # over the mask. That is GRPO's definition, and it makes the shaped and
        # unshaped arms of the study the same estimator.
        scores = [1.0, 0.0, 1.0, 1.0]
        rewards = [[0.0, 0.0, s] for s in scores]
        adv, _ = self.call(rewards, index=np.zeros(4, dtype=object))

        mean = sum(scores) / len(scores)
        var = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = var**0.5
        for i, s in enumerate(scores):
            expected = (s - mean) / (std + 1e-6)
            self.assertAlmostEqual(float(adv[i, 0]), expected, places=4)
            self.assertTrue(torch.allclose(adv[i], torch.full((3,), adv[i, 0])))

    def test_shaping_moves_credit_inside_a_rollout_but_not_between_rollouts(self):
        # Two rollouts, same outcome, same total potential change, different
        # timing: A gains early, B gains late. Potential-based shaping must
        # leave their turn-0 return-to-go identical — the policy-invariance
        # guarantee — while separating them at turn 1.
        a = [0.0, 0.4, 0.1 + 1.0]   # phi 0.5 -> 0.9 -> 1.0, outcome 1.0
        b = [0.0, -0.4, 0.9 + 1.0]  # phi 0.5 -> 0.1 -> 1.0, outcome 1.0
        adv, _ = self.call([a, b], index=np.zeros(2, dtype=object))
        self.assertAlmostEqual(float(adv[0, 0]), float(adv[1, 0]), places=5)
        self.assertGreater(float(adv[1, 2]), float(adv[0, 2]))

    def test_explicit_turn_boundaries_beat_inference_from_nonzeros(self):
        # A middle turn that happened to score exactly zero would be invisible
        # to boundary inference; passing the generator's own offsets fixes it.
        rewards = [[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0]]
        inferred, _ = self.call(rewards)
        explicit, _ = self.call(rewards, turn_boundaries=[[1, 3], [1, 3]])
        self.assertEqual(inferred.shape, explicit.shape)
        self.assertTrue(torch.all(explicit[0, :2] == explicit[0, 0]))

    def test_registration_is_a_no_op_without_skyrl(self):
        try:
            import skyrl_train  # noqa: F401
        except ImportError:
            self.assertFalse(register())
            return
        self.assertTrue(register(ESTIMATOR_NAME))  # pragma: no cover


if __name__ == "__main__":
    unittest.main(verbosity=2)
