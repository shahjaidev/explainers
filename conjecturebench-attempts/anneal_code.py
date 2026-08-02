"""Search for record-beating linear codes via the projective multiset view.

A [n,k,d]_q code <=> multiset S of n points of PG(k-1,q);
d = n - max_H |S \cap H| over hyperplanes H.
Minimize m(S) = max hyperplane count (lexicographically with #achievers).
"""
import numpy as np, sys, time, random

def gf_tables(q):
    if q in (2, 3, 5):  # prime fields
        add = np.array([[(a + b) % q for b in range(q)] for a in range(q)], dtype=np.int8)
        mul = np.array([[(a * b) % q for b in range(q)] for a in range(q)], dtype=np.int8)
    elif q == 4:  # GF(4): bits, add = xor, mul via poly x^2+x+1
        add = np.array([[a ^ b for b in range(4)] for a in range(4)], dtype=np.int8)
        mul = np.zeros((4, 4), dtype=np.int8)
        def m(a, b):
            r = 0
            x = a
            for i in range(2):
                if (b >> i) & 1:
                    r ^= x
                # multiply x by w (poly x): shift, reduce by w^2 = w+1 -> 0b11
                x = (x << 1) ^ (0b111 if x & 0b10 else 0)
                x &= 0b11
                # note: recompute properly below
            return r
        # safer: build via exp/log
        # GF(4) elems 0,1,2,3 ; w=2, w^2=3=w+1, w^3=1
        exp = [1, 2, 3]
        log = {1: 0, 2: 1, 3: 2}
        for a in range(4):
            for b in range(4):
                if a == 0 or b == 0:
                    mul[a, b] = 0
                else:
                    mul[a, b] = exp[(log[a] + log[b]) % 3]
    else:
        raise ValueError(q)
    return add, mul

def proj_points(q, k):
    """All points of PG(k-1,q), canonical rep: first nonzero coord = 1."""
    pts = []
    def rec(prefix):
        if len(prefix) == k:
            return
        # first nonzero at position len(prefix) is 1
        base = prefix + [1]
        # remaining coords free
        rem = k - len(base)
        for tail in np.ndindex(*([q] * rem)):
            pts.append(base + list(tail))
        rec(prefix + [0])
    rec([])
    return np.array(pts, dtype=np.int8)

class Searcher:
    def __init__(self, q, k, n, seed=0):
        self.q, self.k, self.n = q, k, n
        self.add, self.mul = gf_tables(q)
        self.P = proj_points(q, k)          # points, shape (N,k)
        self.N = len(self.P)
        self.rng = random.Random(seed)
        # incidence: point p on hyperplane h iff h . p == 0
        # we compute rows lazily: for point vector v, dot with all hyperplane vecs (=P)
    def dots_with_all(self, v):
        # sum over coords of mul[P[:,i], v[i]] in GF(q)
        acc = np.zeros(self.N, dtype=np.int8)
        for i in range(self.k):
            prod = self.mul[self.P[:, i], v[i]]
            acc = self.add[acc, prod]
        return acc
    def hyps_through(self, pt_idx):
        if pt_idx not in self._cache:
            v = self.P[pt_idx]
            self._cache[pt_idx] = np.flatnonzero(self.dots_with_all(v) == 0)
        return self._cache[pt_idx]
    def eval_counts(self, sel):
        counts = np.zeros(self.N, dtype=np.int32)
        for idx in sel:
            counts[self.hyps_through(idx)] += 1
        return counts
    def search(self, time_budget, target_max, init=None, cache_cap=6000):
        self._cache = {}
        n, N, rng = self.n, self.N, self.rng
        sel = list(init) if init is not None else [rng.randrange(N) for _ in range(n)]
        counts = self.eval_counts(sel)
        def score(c):
            mx = int(c.max())
            return (mx, int((c == mx).sum()))
        best = score(counts)
        best_sel = sel[:]
        t0 = time.time()
        it = 0
        T = 1.0
        while time.time() - t0 < time_budget:
            it += 1
            T = max(0.02, 1.0 * (1 - (time.time() - t0) / time_budget))
            # pick a point contributing to a max hyperplane (intensify) or random
            mx = counts.max()
            if rng.random() < 0.8:
                hmax = np.flatnonzero(counts == mx)
                h = int(hmax[rng.randrange(len(hmax))])
                # find a selected point on h
                cand = [j for j, idx in enumerate(sel)
                        if h in set(self.hyps_through(idx))] if n < 60 else None
                if cand:
                    j = rng.choice(cand)
                else:
                    j = rng.randrange(n)
            else:
                j = rng.randrange(n)
            old = sel[j]
            new = rng.randrange(N)
            if new == old:
                continue
            ho, hn = self.hyps_through(old), self.hyps_through(new)
            counts[ho] -= 1
            counts[hn] += 1
            s = score(counts)
            cur = score(counts)  # after move
            # accept if better or with annealing prob
            # compare to previous score: recompute previous quickly
            counts[hn] -= 1
            counts[ho] += 1
            prev = score(counts)
            delta = (cur[0] - prev[0]) * N + (cur[1] - prev[1])
            if delta <= 0 or rng.random() < np.exp(-delta / (T * max(1, N // 200))):
                counts[ho] -= 1
                counts[hn] += 1
                sel[j] = new
                if cur < best:
                    best = cur
                    best_sel = sel[:]
                    if best[0] <= target_max:
                        break
            if len(self._cache) > cache_cap:
                self._cache.clear()
                for idx in set(sel):
                    self.hyps_through(idx)
        return best, best_sel, it

def main():
    q, k, n, target_max, budget = (int(x) for x in sys.argv[1:6])
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    cap = int(sys.argv[7]) if len(sys.argv) > 7 else 6000
    s = Searcher(q, k, n, seed)
    print(f"PG({k-1},{q}): {s.N} points; want max hyperplane count <= {target_max} "
          f"(d >= {n - target_max})", flush=True)
    best, sel, it = s.search(budget, target_max, cache_cap=cap)
    d = n - best[0]
    print(f"iters={it} best max-count={best[0]} (achieved by {best[1]} hyperplanes) -> d={d}")
    np.save(f"best_{q}_{k}_{n}.npy", np.array(sel))

if __name__ == "__main__":
    main()
