"""Where potential-based shaping plugs into a trainer.

prime-rl's Algorithms layer answers "given a finalised rollout with rewards,
what per-token signal does it produce". Turn-level potentials are one level
above that, so this module does the turn -> token expansion explicitly:

    per-turn potential phi[0..T]
        -> potential-based shaping F_t = gamma*phi[t+1] - phi[t]
        -> outcome added to the final transition
        -> group-relative advantage (GRPO) over the rollout group
        -> broadcast to the tokens of each turn's <action> span

Nothing here is framework-specific; :func:`token_advantages` returns plain
lists that a prime-rl algorithm, a SkyRL advantage estimator, or a verl-agent
adapter can consume. The framework-shaped wrappers are at the bottom.

The one non-obvious choice: advantages are broadcast only over trainable
spans. Observation tokens are environment-generated and carry no gradient —
see ``irrev.protocol.loss_mask``.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from irrev.shaping import assemble_rewards


def group_relative_advantages(
    returns: Sequence[float], eps: float = 1e-6, normalise: bool = True
) -> List[float]:
    """GRPO-style: centre on the group mean, optionally scale by group std."""
    n = len(returns)
    if n == 0:
        return []
    mean = sum(returns) / n
    centred = [r - mean for r in returns]
    if not normalise or n == 1:
        return centred
    var = sum(c * c for c in centred) / n
    std = var**0.5
    return [c / (std + eps) for c in centred]


def turn_returns(
    outcome: float,
    phi: Sequence[float],
    gamma: float = 1.0,
    mode: str = "potential",
    scale: float = 1.0,
) -> List[float]:
    """Discounted return-to-go per turn, from shaped rewards."""
    rewards = assemble_rewards(outcome, phi, gamma=gamma, mode=mode, scale=scale)
    out: List[float] = [0.0] * len(rewards)
    running = 0.0
    for t in range(len(rewards) - 1, -1, -1):
        running = rewards[t] + gamma * running
        out[t] = running
    return out


def token_advantages(
    turn_advantage: Sequence[float],
    turn_token_spans: Sequence[Tuple[int, int]],
    n_tokens: int,
    trainable: Optional[Sequence[int]] = None,
) -> List[float]:
    """Broadcast a per-turn advantage over that turn's trainable tokens.

    *turn_token_spans* are ``(start, end)`` token indices for each turn's
    action span, in order. Tokens outside any span — the prompt, observation
    text — get zero.
    """
    adv = [0.0] * n_tokens
    for value, (start, end) in zip(turn_advantage, turn_token_spans):
        for i in range(max(0, start), min(n_tokens, end)):
            if trainable is None or trainable[i]:
                adv[i] = value
    return adv


def build_group_advantages(
    group: Sequence[Dict],
    gamma: float = 1.0,
    mode: str = "potential",
    scale: float = 1.0,
    normalise: bool = True,
) -> List[List[float]]:
    """Full path for one GRPO group.

    Each element of *group* is a dict with keys ``outcome``, ``phi``,
    ``token_spans``, ``n_tokens`` and optionally ``trainable``.

    Advantages are group-normalised *per turn index*: turn t of every rollout
    is centred on the mean return-to-go at turn t across the group. Rollouts
    are ragged, so each index uses only the rollouts that reached it. With no
    shaping (``mode="none"``) every turn of a rollout carries the same
    return-to-go and this degenerates to ordinary outcome GRPO, which is the
    property that makes the comparison in the study fair.
    """
    per_rollout_returns = [
        turn_returns(r["outcome"], r["phi"], gamma=gamma, mode=mode, scale=scale)
        for r in group
    ]
    longest = max((len(r) for r in per_rollout_returns), default=0)

    turn_adv: List[List[float]] = [[0.0] * len(rets) for rets in per_rollout_returns]
    for t in range(longest):
        members = [i for i, rets in enumerate(per_rollout_returns) if t < len(rets)]
        values = [per_rollout_returns[i][t] for i in members]
        for i, adv in zip(members, group_relative_advantages(values, normalise=normalise)):
            turn_adv[i][t] = adv

    return [
        token_advantages(
            adv, rollout["token_spans"], rollout["n_tokens"], rollout.get("trainable")
        )
        for rollout, adv in zip(group, turn_adv)
    ]


# --------------------------------------------------------------------------
# Framework wrappers. Both are thin: the arithmetic above is the whole idea.
# --------------------------------------------------------------------------


def prime_rl_algorithm(gamma: float = 1.0, mode: str = "potential", scale: float = 1.0):
    """Return a callable with the shape prime-rl's Algorithms layer expects."""

    def compute_advantages(rollouts):
        group = [
            {
                "outcome": r.reward,
                "phi": r.metadata.get("phi", [0.0, 0.0]),
                "token_spans": r.metadata["action_token_spans"],
                "n_tokens": len(r.token_ids),
                "trainable": r.metadata.get("loss_mask"),
            }
            for r in rollouts
        ]
        return build_group_advantages(group, gamma=gamma, mode=mode, scale=scale)

    return compute_advantages


def skyrl_advantage_fn(gamma: float = 1.0, mode: str = "potential", scale: float = 1.0):
    """Same thing, keyed for SkyRL's trajectory dicts."""

    def fn(trajectories):
        group = [
            {
                "outcome": t["reward"],
                "phi": t.get("phi", [0.0, 0.0]),
                "token_spans": t["action_token_spans"],
                "n_tokens": len(t["token_ids"]),
                "trainable": t.get("loss_mask"),
            }
            for t in trajectories
        ]
        return build_group_advantages(group, gamma=gamma, mode=mode, scale=scale)

    return fn
