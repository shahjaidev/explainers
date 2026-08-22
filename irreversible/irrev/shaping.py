"""Reward assembly.

The teacher's step scores are used as a *potential function*, not as reward.
Potential-based shaping (Ng, Harada & Russell, ICML 1999) is policy-invariant:
adding ``gamma * phi(s') - phi(s)`` to every transition changes the discounted
return by exactly ``gamma^T phi(s_T) - phi(s_0)``, a constant with respect to
the policy's behaviour in between. It can change how fast you learn; it
provably cannot change what you learn toward.

:func:`naive_shaping` is the ablation arm — raw teacher scores as rewards,
with no such guarantee. The predicted failure is an agent that narrates
confidently and acts badly, because the critic reads a well-formed
``<thought>`` before the action executes.
"""

from __future__ import annotations

from typing import List, Sequence


def potential_shaping(phi: Sequence[float], gamma: float = 1.0) -> List[float]:
    """``F_t = gamma * phi[t+1] - phi[t]`` for each of the T transitions.

    *phi* has ``T + 1`` entries: the potential before the first action, then
    one after each action.
    """
    if len(phi) < 2:
        return []
    return [gamma * phi[t + 1] - phi[t] for t in range(len(phi) - 1)]


def naive_shaping(phi: Sequence[float]) -> List[float]:
    """Raw teacher score as the step reward. The hackable arm."""
    return list(phi[1:])


def discounted_return(rewards: Sequence[float], gamma: float = 1.0) -> float:
    return sum((gamma ** t) * r for t, r in enumerate(rewards))


def assemble_rewards(
    outcome: float,
    phi: Sequence[float],
    gamma: float = 1.0,
    mode: str = "potential",
    scale: float = 1.0,
) -> List[float]:
    """Per-step rewards: shaping on every transition, outcome on the last."""
    if mode == "potential":
        shaped = potential_shaping(phi, gamma)
    elif mode == "naive":
        shaped = naive_shaping(phi)
    elif mode == "none":
        shaped = [0.0] * max(0, len(phi) - 1)
    else:
        raise ValueError(f"unknown shaping mode {mode!r}")
    rewards = [scale * s for s in shaped]
    if not rewards:
        return [outcome]
    rewards[-1] += outcome
    return rewards


def shaping_is_policy_invariant(phi: Sequence[float], gamma: float = 1.0, tol: float = 1e-9) -> bool:
    """Check the telescoping identity that makes the shaping safe."""
    shaped = potential_shaping(phi, gamma)
    lhs = discounted_return(shaped, gamma)
    T = len(shaped)
    rhs = (gamma ** T) * phi[-1] - phi[0]
    return abs(lhs - rhs) < tol
