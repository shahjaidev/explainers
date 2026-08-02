# ConjectureBench: five random problems, attempted

Source: [bespokelabsai/conjecture-bench](https://github.com/bespokelabsai/conjecture-bench)
(14,865 open-problem records). Five records were drawn uniformly at random
(`random.sample` over the full exported stream); see `picked_problems.json`.
Attempts made 2026-08-02.

## Results at a glance

| Problem | Status of attempt |
| --- | --- |
| unsolvedmath-1861 — Erdős prize problem on large prime gaps | **Resolved in the literature** — catalog entry is stale; answer is *yes* |
| ljcr-ds-28800-930-30-12-2400 — (28800, 930, 30)-difference set in Z₁₂×Z₂₄₀₀ | No progress; verified that every classical nonexistence tool is inapplicable |
| codetables-gf2-109-14 — binary [109,14], best known d=45, need 46 | Best found: **d=43** (shortened+punctured BCH) |
| codetables-gf4-199-7 — [199,7] over GF(4), best known d=140, need 141 | Best found: **d=135** (projective multiset annealing) |
| codetables-gf5-98-8 — [98,8] over GF(5), best known d=69, need 70 | Best found: **d=64** (projective multiset annealing) |

## 1. Erdős prime-gap problem (unsolvedmath-1861)

The record asks whether for infinitely many n,
d_n = p_{n+1} − p_n > c·(ln n · ln ln n · ln ln ln ln n)/(ln ln ln n)² holds for
*arbitrarily large* constant c (Rankin's 1938 bound with c → ∞; Erdős's largest
prize, $10,000).

This was **proved in 2014**, independently by James Maynard
([arXiv:1408.5110](https://arxiv.org/abs/1408.5110)) and by Ford–Green–Konyagin–Tao
([arXiv:1408.4505](https://arxiv.org/abs/1408.4505)), both published in Annals of
Mathematics (2016). The five authors jointly improved the bound further in
"Long gaps between primes" (JAMS 2018), replacing (ln ln ln n)² by ln ln ln n.
The catalog's `open` status (as of 2026-05-13) is stale.

## 2. (28800, 930, 30)-difference set in Z₁₂ × Z₂₄₀₀

Existence is open. Checks performed (see session notes):

- Counting identity k(k−1) = λ(v−1): 930·929 = 30·28799 ✓ — parameters admissible.
- Order n = k − λ = 900 = 2²·3²·5². For the Turyn/Ma self-conjugacy machinery,
  a prime p must be self-conjugate mod exp(G) = 2400. Computed orders show
  **none of 2, 3, 5 is self-conjugate mod 2400**, so those nonexistence
  arguments never engage.
- Every prime factor of n divides v = 28800, so the first and second multiplier
  theorems are inapplicable (they need a multiplier prime coprime to v).
- Small quotient contractions (order 2, 3) are integrally feasible
  (e.g. order 2: 480/450 split with (a−b)² = 900).

Conclusion: the problem genuinely survives the standard toolkit — the modern
field-descent method (Schmidt) is the only remaining general tool, and direct
search is hopeless at C(28800, 930) states. No progress on existence either;
the group has 900 = |n| square, and no known family (McFarland, Davis–Jedwab,
Chen, Hadamard) matches these parameters.

## 3–5. Best-known linear code distances (codetables families)

All three use the projective-geometry equivalence: an [n,k,d]_q code is a
multiset S of n points of PG(k−1,q) with d = n − max_H |S ∩ H| over hyperplanes H.
Since k ≤ 14, min distance is exactly evaluable (≤ 5⁸ codewords), so local
search is exact. Two attacks:

- `anneal_code.py` — simulated annealing over point multisets, with incremental
  hyperplane-count updates. Verified correct by recovering the optimal
  [15,4,8]₂ simplex, [21,3,16]₄, and [31,3,24]₅ codes.
- `bch_puncture.py` / `bch_anneal.py` (binary [109,14] only) — construct the
  [127,15,55] BCH code (verified min weight 55 by full enumeration), shorten
  once to [126,14,55], then choose 17 columns to delete: greedy gives
  [109,14,43]; annealing over deletion 17-subsets (90 restarts, ~9 min)
  also plateaus at **d=43**.

Outcomes (each ~9 min of search):

| Target | Record / needed | Pure anneal | BCH route |
| --- | --- | --- | --- |
| [109,14]₂ | 45 / 46 | 39 | **43** |
| [199,7]₄ | 140 / 141 | **135** | — |
| [98,8]₅ | 69 / 70 | **64** | — |

No records were broken. The gap (2–6 below best known) matches expectations:
codetables entries are the accumulation of decades of bespoke algebraic
constructions (quasi-cyclic searches, Griesmer-optimal chains, concatenations),
and generic stochastic search reliably lands a few units short. The most
promising unexplored direction for [109,14]₂ is a dedicated quasi-cyclic /
quasi-twisted search at length 112 followed by shortening, which is how many
neighboring codetables entries were produced.

## Files

- `picked_problems.json` — the five records as sampled
- `anneal_code.py` — projective multiset annealer (any q ∈ {2,3,4,5})
- `bch_puncture.py` — BCH [127,15,55] construction + greedy shorten/puncture
- `bch_anneal.py` — annealing over puncture sets of the shortened BCH code
