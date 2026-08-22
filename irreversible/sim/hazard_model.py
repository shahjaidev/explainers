"""The analytic prediction.

If each step independently has hazard *h* of destroying protected data, and
the agent can walk back *K* steps, a trajectory survives iff the number of
hazards is within budget::

    success(K) = base * P(Binomial(H, h) <= K)

Process supervision is modelled as lowering the hazard, ``h -> h(1-r)``. The
advantage is the gap between two binomial tails: largest at K=0, vanishing as
K passes the expected hazard count H*h.

This is the same arithmetic the explainer page plots. ``test_all.py`` asserts
the two agree, so the figure and the code cannot drift apart.
"""

from __future__ import annotations

from typing import Dict, List, Sequence


def binom_cdf(n: int, p: float, k: int) -> float:
    """P(Binomial(n, p) <= k), computed by forward recurrence."""
    if k >= n:
        return 1.0
    if k < 0:
        return 0.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    term = (1 - p) ** n
    total = term
    for i in range(1, k + 1):
        term *= (n - i + 1) / i * (p / (1 - p))
        total += term
    return min(1.0, total)


def success(horizon: int, hazard: float, budget: int, base: float = 1.0) -> float:
    return base * binom_cdf(horizon, hazard, budget)


def advantage_curve(
    horizon: int = 12,
    hazard: float = 0.10,
    reduction: float = 0.45,
    base: float = 0.70,
    budgets: Sequence[int] = (0, 1, 2, 3, 4, 5, 6, 8, 10, 12),
) -> List[Dict[str, float]]:
    """The predicted money plot, one row per undo budget."""
    supervised = hazard * (1 - reduction)
    rows = []
    for k in budgets:
        out = success(horizon, hazard, k, base)
        prm = success(horizon, supervised, k, base)
        rows.append({"K": k, "outcome_only": out, "process": prm, "advantage": prm - out})
    return rows


def crossover(rows: Sequence[Dict[str, float]], tol: float = 0.01) -> float:
    """Smallest K at which the predicted advantage falls below *tol*."""
    for row in rows:
        if row["advantage"] < tol:
            return row["K"]
    return float("inf")


if __name__ == "__main__":
    rows = advantage_curve()
    print(f"{'K':>4} {'outcome-only':>13} {'process':>9} {'advantage':>10}")
    for r in rows:
        print(f"{r['K']:>4} {r['outcome_only']:>13.3f} {r['process']:>9.3f} {r['advantage']:>10.3f}")
    print(f"\ncrossover (advantage < 1pt): K = {crossover(rows)}")
