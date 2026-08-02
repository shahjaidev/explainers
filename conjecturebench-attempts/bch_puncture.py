"""[127,15,55] BCH -> shorten 1 -> greedily puncture 17 cols -> [109,14,d]."""
import numpy as np

# GF(128) via primitive poly x^7+x^3+1 (0b10001001)
POLY = 0b10001001
def gmul(a, b):
    r = 0
    while b:
        if b & 1: r ^= a
        b >>= 1
        a <<= 1
        if a & 0x80: a ^= POLY
    return r

# cyclotomic cosets of 2 mod 127
seen, cosets = set(), []
for i in range(1, 127):
    if i in seen: continue
    c, x = [], i
    while x not in c:
        c.append(x); seen.add(x)
        x = x * 2 % 127
    cosets.append(sorted(c))

# defining set: cosets meeting {1..delta-1}; find delta giving k=15
need = set()
delta = 55
for c in cosets:
    if any(1 <= e <= delta - 1 for e in c):
        need |= set(c)
k = 127 - len(need)
print("defining set size", len(need), "-> k =", k)

# generator polynomial = prod of (x - alpha^e) for e in defining set, over GF(128),
# result has GF(2) coeffs
g = [1]
alpha = 2
apow = [1]
for _ in range(127):
    apow.append(gmul(apow[-1], alpha))
for e in sorted(need):
    root = apow[e]
    # multiply g by (x + root)
    ng = [0] * (len(g) + 1)
    for i, co in enumerate(g):
        ng[i + 1] ^= co        # x * g  (GF(2^7) add = xor)
        ng[i] ^= gmul(co, root)
    g = ng
assert all(co in (0, 1) for co in g), "generator not binary!"
g = np.array(g, dtype=np.uint8)
print("deg g =", len(g) - 1)

# generator matrix of cyclic code: shifts of g
K = 127 - (len(g) - 1)
G = np.zeros((K, 127), dtype=np.uint8)
for i in range(K):
    G[i, i:i + len(g)] = g

# all 2^15 codewords via messages
msgs = ((np.arange(1 << K)[:, None] >> np.arange(K)) & 1).astype(np.uint8)
C = msgs @ G % 2
w = C.sum(1)
print("full code: min weight =", w[1:].min())

# shorten at position 0: keep codewords with 0 there, drop coord
keep = C[:, 0] == 0
Cs = C[keep][:, 1:]
# dimension check
print("shortened: #codewords =", keep.sum(), " (expect 2^14)")
ws = Cs.sum(1)
print("shortened min weight =", ws[ws > 0].min(), " n =", Cs.shape[1])

# greedy puncturing: delete 17 columns; maximize min weight, tie-break on count
cur = Cs.astype(np.int32)
for step in range(17):
    n = cur.shape[1]
    w = cur.sum(1)
    nz = w > 0
    best = None
    colsums_at_min = None
    mn = w[nz].min()
    # deleting col j reduces weight of codewords having 1 there.
    # new min weight = min over c of w(c) - c[j]; evaluate all j at once
    delw = w[:, None] - cur  # shape (M, n): weight after deleting col j
    delw = np.where(nz[:, None], delw, 10**9)
    newmin = delw.min(0)
    cand = np.flatnonzero(newmin == newmin.max())
    # tie-break: fewest codewords at the new min
    counts = (delw[:, cand] == newmin.max()).sum(0)
    j = cand[np.argmin(counts)]
    cur = np.delete(cur, j, axis=1)
    print(f"step {step+1}: deleted col {j}, n={cur.shape[1]}, min weight -> {newmin.max()}, #at-min {counts.min()}")
final_w = cur.sum(1)
print("FINAL: [%d,14,%d] code" % (cur.shape[1], final_w[final_w > 0].min()))
