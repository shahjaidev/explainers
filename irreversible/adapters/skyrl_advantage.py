"""SkyRL adapter — potential-shaped advantages as a registered estimator.

SkyRL's contract (skyrl-train 0.3.1, ``skyrl_train/utils/ppo_utils.py``) is::

    @register_advantage_estimator("name")
    def fn(token_level_rewards: Tensor[B, T],
           response_mask:       Tensor[B, T],
           index:               np.ndarray[B],     # group id per rollout
           epsilon: float = 1e-6,
           grpo_norm_by_std: bool = True,
           **kwargs) -> tuple[advantages Tensor[B, T], returns Tensor[B, T]]

Their GRPO estimator sums ``token_level_rewards`` to one score per sequence and
broadcasts a group-normalised advantage over the mask — which is exactly the
outcome-only arm of the study, and exactly what discards the information a
process reward model provides.

This estimator keeps the per-turn structure instead. It assumes the generator
placed the potential-based shaping reward at the last token of each turn's
``<action>`` span (see ``irrev.shaping``), reads those positions as turn
boundaries, computes return-to-go per turn, and group-normalises **per turn
index** — turn t of every rollout in a group is centred on the mean return-to-go
at turn t, using only the rollouts that got that far.

Two properties worth stating, both asserted in ``tests/test_skyrl_adapter.py``:

* With rewards only at the final token — no shaping — it reduces exactly to
  GRPO's outcome advantage. The comparison in the study is then apples to
  apples: the same estimator, with and without the teacher's potentials.
* Potential-based shaping cannot change which trajectory the group prefers,
  only where inside a rollout the credit lands. That is the Ng/Harada/Russell
  guarantee surviving the trip through the tensor layout.

The arithmetic lives in :mod:`adapters.prime_rl_shaping` as plain lists; this
module is the tensor shim. Torch is imported lazily, so the harness itself
stays dependency-free.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .prime_rl_shaping import group_relative_advantages

ESTIMATOR_NAME = "potential_shaped"


def _turn_returns_from_rewards(rewards: Sequence[float], gamma: float) -> List[float]:
    """Return-to-go at each turn, from that turn's reward onward."""
    out = [0.0] * len(rewards)
    running = 0.0
    for t in range(len(rewards) - 1, -1, -1):
        running = rewards[t] + gamma * running
        out[t] = running
    return out


def advantages_from_turns(
    turn_rewards: Sequence[Sequence[float]],
    groups: Sequence,
    gamma: float = 1.0,
    epsilon: float = 1e-6,
    norm_by_std: bool = True,
) -> List[List[float]]:
    """Per-turn advantages for a batch of ragged rollouts.

    *turn_rewards[i]* are rollout i's per-turn rewards (shaping already folded
    in, outcome on the last turn); *groups[i]* is its GRPO group id.
    """
    returns = [_turn_returns_from_rewards(r, gamma) for r in turn_rewards]
    out: List[List[float]] = [[0.0] * len(r) for r in returns]

    by_group = {}
    for i, gid in enumerate(groups):
        by_group.setdefault(gid, []).append(i)

    for members in by_group.values():
        longest = max((len(returns[i]) for i in members), default=0)
        for t in range(longest):
            present = [i for i in members if t < len(returns[i])]
            values = [returns[i][t] for i in present]
            centred = group_relative_advantages(values, eps=epsilon, normalise=norm_by_std)
            for i, adv in zip(present, centred):
                out[i][t] = adv
    return out


def compute_potential_shaped_advantage(
    token_level_rewards,
    response_mask,
    index,
    epsilon: float = 1e-6,
    grpo_norm_by_std: bool = True,
    gamma: float = 1.0,
    turn_boundaries: Optional[Sequence[Sequence[int]]] = None,
    **kwargs,
):
    """SkyRL-signature estimator. Returns ``(advantages, returns)``, both [B, T].

    Turn boundaries are the token positions carrying a non-zero reward, unless
    *turn_boundaries* is passed explicitly — a rollout whose middle turns scored
    exactly zero would otherwise look like it had fewer turns, so a generator
    that knows its own ``</action>`` offsets should pass them.
    """
    import torch

    rewards = token_level_rewards.detach().to(torch.float64)
    mask = response_mask.detach().to(torch.float64)
    batch, _ = rewards.shape
    groups = [index[i] for i in range(batch)]

    positions: List[List[int]] = []
    turn_rewards: List[List[float]] = []
    for i in range(batch):
        row = rewards[i] * mask[i]
        if turn_boundaries is not None:
            pos = [int(p) for p in turn_boundaries[i]]
        else:
            pos = [int(p) for p in torch.nonzero(row, as_tuple=False).flatten().tolist()]
        if not pos:
            # No reward anywhere: one empty turn at the last unmasked token.
            live = torch.nonzero(mask[i], as_tuple=False).flatten()
            pos = [int(live[-1])] if len(live) else [0]
        positions.append(pos)
        turn_rewards.append([float(row[p]) for p in pos])

    per_turn = advantages_from_turns(
        turn_rewards, groups, gamma=gamma, epsilon=epsilon, norm_by_std=grpo_norm_by_std
    )

    advantages = torch.zeros_like(rewards)
    for i, (pos, adv) in enumerate(zip(positions, per_turn)):
        start = 0
        for p, value in zip(pos, adv):
            # A turn's advantage covers its own tokens: everything since the
            # previous boundary, up to and including this one.
            advantages[i, start : p + 1] = value
            start = p + 1
    advantages = advantages * mask
    return advantages.to(token_level_rewards.dtype), advantages.to(token_level_rewards.dtype)


def register(name: str = ESTIMATOR_NAME) -> bool:
    """Register with SkyRL if it is importable. Returns whether it registered."""
    try:
        from skyrl_train.utils.ppo_utils import AdvantageEstimatorRegistry
    except ImportError:
        return False
    AdvantageEstimatorRegistry.register(name, compute_potential_shaped_advantage)
    return True
