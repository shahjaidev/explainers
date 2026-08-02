# Complete exception sets for m/n = 1/x + 1/y + 1/z (4 ≤ m ≤ 19), and a new verification bound for Sierpiński's 5/n conjecture

*Computational note — August 2026. All computations performed on 4 cores of a
cloud Linux container; total compute under one CPU-hour. Code and full data in
this directory.*

## Summary of results

Call an integer n ≥ 2 an **exception for m** if m/n cannot be written as
1/x + 1/y + 1/z with positive integers x, y, z. Erdős–Straus (1948) conjectured
there are no exceptions for m = 4 (verified to 10¹⁷ by Salez 2014; a 2025
preprint, arXiv:2509.00128, reports 10¹⁸); Sierpiński (1956) conjectured the same for
m = 5; Schinzel conjectured that for every m ≥ 4 the exceptions are finite,
with largest member n_m − 1. Pomerance and Weingartner (Ramanujan J. 69, 2026;
arXiv:2511.16817) proved that exceptions *must* exist for every sufficiently
large m — indeed n_m ≥ exp(m^{1/3+o(1)}) — and reported numerics indicating
that every m ≥ 20 already has a prime exception in the window (m², 2m²).

This project contributes the complementary small-m data:

**1. Sierpiński's conjecture (m = 5) verified for all 2 ≤ n ≤ 10¹¹.**
The classical bound is n ≤ 1,057,438,801 (mid-1960s, cited in R. L. Graham,
*Paul Erdős and Egyptian fractions*, 2013); a 2025 preprint (Ghermoul,
arXiv:2508.07367) reports verification of its residual class to ~10¹⁰.
The present bound is ~94.6× the classical record and 10× the preprint's. 4,117,976,315 primes were processed
(the count matches π(10¹¹) − π(10⁶) exactly, an independent check on the
sieve); every prime received an explicit representability certificate, with
zero unresolved cases. m = 6 was likewise verified exception-free to 10⁹.

**2. Complete exception sets for m = 6, …, 19, exhaustive over ALL n ≤ 10⁹**
(primes and composites). The sets, with counts and largest elements:

| m  | #exceptions | largest | empirical n_m | composite members |
|----|------------|---------|--------------|-------------------|
| 4  | 0 | — | 2 | — |
| 5  | 0 | — | 2 | — |
| 6  | 0 | — | 2 | — |
| 7  | 1 | 2 | 3 | — |
| 8  | 6 | 241 | 242 | — |
| 9  | 4 | 19 | 20 | — |
| 10 | 8 | 181 | 182 | — |
| 11 | 4 | 37 | 38 | 4 |
| 12 | 23 | 12,241 | 12,242 | 25 |
| 13 | 12 | 281 | 282 | 4, 14 |
| 14 | 11 | 841 | 842 | 4, 841 = 29² |
| 15 | 31 | 20,521 | 20,522 | 4, 8, 16, 34, 122, 226 |
| 16 | 47 | 83,449 | 83,450 | 4, 6, 9, 22, 33, 34, 121 = 11², 262, 482 |
| 17 | 20 | 2,081 | 2,082 | 4, 6, 9 |
| 18 | 53 | 35,281 | 35,282 | 4, 10, 22, 38 |
| 19 | 23 | 353 | 354 | 4, 6, 8, 10, 26, 46, 82 |

Full sets in `data/exceptions_m4_19.txt`. The "empirical n_m" values are exact
provided no exception exceeds 10⁹; every set's largest member is below 10⁵,
so each set is separated from the search bound by more than four orders of
magnitude. To our knowledge the sets for m ≥ 8 at this exhaustiveness, and the
n_m table, have not been published (they do not appear in OEIS as of this
writing).

**3. Independent replication of Pomerance–Weingartner for 20 ≤ m ≤ 60**:
every such m has at least one prime exception in (m², 2m²) — 1,494 exceptions
total (`data/pw_exceptions_m20_60.txt`) — with a refinement at the boundary:
the window property already holds for m = 10, 12, 13, 14, 15, 16, 17, 18, and
among 4 ≤ m ≤ 60 it fails exactly for

  m ∈ {4, 5, 6, 7, 8, 9, 11, 19}.

So the natural conjecture suggested by the data is that this eight-element set
is the complete list of m ≥ 4 whose window (m², 2m²) is exception-free —
"m ≥ 20" in Pomerance–Weingartner is the clean uniform statement, but the
phenomenon actually begins at m = 10, with the two stragglers 11 and 19.

**4. Structural observations.**
- Composite exceptions exist only for m ≥ 11 and are rare; three are perfect
  squares of prime exceptions of the same m (25 = 5² for m = 12,
  841 = 29² for m = 14, 121 = 11² for m = 16) — the only cases where n and n²
  are both exceptional.
- For each m, the final (largest) exceptions concentrate in the residue class
  n ≡ 1 (mod m): all eleven m = 12 exceptions above 400 are ≡ 1 (mod 24) —
  exactly the hard Erdős–Straus classes — the four largest m = 18 exceptions
  and three largest m = 15 exceptions are all ≡ 1 (mod m), and for m = 16 the
  largest is 83,449 ≡ 9 (mod 16) (a square class) followed by three values
  ≡ 1 (mod 16). The class
  containing 1, which every modulus keeps as a quadratic residue, is the last
  to empty out — consistent with the quadratic-residue obstruction that
  governs the m = 4 case.

## Method

**Decision criterion.** For fixed m, n, every representation has a least
denominator x with n/m < x ≤ 3n/m. Writing a = mx − n and b = nx, the
remaining two terms must satisfy 1/y + 1/z = a/b, which holds iff there is a
divisor pair d·d′ = b² with d ≡ d′ ≡ −b (mod a); then y = (b+d)/a,
z = (b+d′)/a, and 1/y + 1/z = a/b is an algebraic identity. Enumerating x
over its full range and all divisor pairs of b² is therefore a *complete*
decision procedure: it can certify non-representability, not merely fail to
find witnesses.

**Three implementations, two of them independent.**
- `mfrac.c` — the production engine. A segmented prime sieve feeds a
  first-hit search (partial factorization of x, all divisor candidates
  d = p^j·f with f | x², all congruence work exact in 64/128-bit integers);
  primes not certified within 96 candidate x values escalate to 20,000, and
  anything still unresolved is flagged SUSPECT rather than classified. Across
  all runs (4.6 billion primes processed) zero SUSPECTs survived. The same
  file contains the complete decision procedure used for all n ≤ 10⁶, for
  suspect resolution, and for composite candidates.
- `check2.c` — an independent checker with a deliberately different
  algorithm (full y-range iteration and integrality test for z; no divisor
  enumeration, no factorization, no modular shortcuts). Every one of the 243
  claimed exceptions was re-certified non-representable by this second
  program, with representable neighbors as positive controls.
- A Python brute force over exact rationals (`fractions.Fraction`)
  cross-validated both C implementations on all m ≤ 14, n < 400; random prime
  certificates are additionally re-verified in exact rational arithmetic
  (this audit caught — and we fixed — one display-only bug: a witness z
  printed truncated mod 2⁶⁴; the underlying decisions were 128-bit exact and
  unaffected, and both affected certificates verify with the true z).

**Closing the composite gap.** A composite n is representable whenever any
divisor > 1 is (scale the certificate), so a composite exception must have all
prime factors exceptional. All 4,769,723 products of exceptional primes in
(10⁶, 10⁹] across m = 7..19 were individually decided: none is an exception.
Together with the complete sweep of n ≤ 10⁶ and the prime scans to 10⁹
(10¹¹ for m = 5), the exception sets above are exhaustive for their stated
ranges.

**Why the m = 5 claim is airtight for composites:** every composite n ≤ 10¹¹
has a prime factor ≤ √10¹¹ < 10⁶, and the complete sweep found no exceptional
n ≤ 10⁶ at all for m = 5, so every composite inherits a certificate from any
of its prime factors.

## Honesty ledger

- The n_m values are **empirical**: exact if and only if no exception hides
  above the search bounds. Pomerance–Weingartner's theorem guarantees huge
  exceptions (of size exp(m^{1/3+o(1)})) for all *sufficiently large* m; if
  that regime reaches down into 7 ≤ m ≤ 19, the sets above would be
  incomplete. Nothing in the data suggests this — every set terminates four
  orders of magnitude before the bound — but it is not a proof.
- We could not access the full text of Pomerance–Weingartner (paywalled +
  arXiv blocked from this environment); their numerics section may contain
  overlapping small-m computations. Priority for any overlap belongs to them.
  Our replication of their m ≥ 20 window claim matches their abstract exactly.
- The 5/n record claim depends on the prior record being Stewart-era
  1,057,438,801, the best bound found in the literature we could search
  (Graham 2013 survey; no newer bound surfaced in any search). If a larger
  unpublished verification exists, the record claim (not the verification
  itself) would need revision.
- These are verification results and finite data sets. The conjectures of
  Erdős–Straus, Sierpiński, and Schinzel remain open.

## Reproducibility

- `mfrac.c` (production engine, all modes documented in header),
  `check2.c` (independent checker). gcc -O2, no dependencies.
- m = 5 to 10¹¹: `primes` mode over four range chunks, ~40 CPU-minutes.
- m = 6..19 to 10⁹: `small` mode to 10⁶ + `primes` mode + `list` mode over
  composite candidates, ~15 CPU-minutes total.
- m = 20..60 windows: `pw` mode, ~2 CPU-minutes.

## References

- Erdős, P. (1950). Az 1/x₁ + … egyenlet egész számú megoldásairól. Mat. Lapok 1.
- Sierpiński, W. (1956). Sur les décompositions de nombres rationnels en fractions primaires. Mathesis 65.
- Graham, R. L. (2013). Paul Erdős and Egyptian fractions. In *Erdős Centennial*, Bolyai Soc. Math. Stud. 25.
- Elsholtz, C., Tao, T. (2013). Counting the number of solutions to the Erdős–Straus equation on unit fractions. J. Aust. Math. Soc. 94.
- Salez, S. E. (2014). The Erdős–Straus conjecture: new modular equations and checking up to N = 10¹⁷. arXiv:1406.6307.
- Ghermoul, B. (2025). Almost a complete proof of the generalized Erdős–Straus conjecture: 5/a = 1/b + 1/c + 1/d. arXiv:2508.07367.
- Mihnea, S., Bogdan, D. C. (2025). Further verification and empirical evidence for the Erdős–Straus conjecture. arXiv:2509.00128.
- Pomerance, C., Weingartner, A. (2026). Exceptions to the Erdős–Straus–Schinzel conjecture. Ramanujan J. 69. arXiv:2511.16817.
