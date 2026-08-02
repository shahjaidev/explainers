"""Anneal over 17-column deletion sets of the shortened [126,14,55] BCH code."""
import numpy as np, random, time, sys

d = np.load
# rebuild shortened code (same as bch_puncture.py)
exec(open('bch_puncture.py').read().split('# greedy puncturing')[0])

Cs = Cs.astype(np.int64)          # (16384, 126), row 0 is zero word
W = Cs.sum(1)                      # full weights
nz = W > 0
Cnz = Cs[nz]
Wnz = W[nz]
M, N = Cnz.shape
DEL = 17
TARGET = 46

def score(S):
    """(min weight, #codewords at min) after deleting columns in list S."""
    loss = Cnz[:, S].sum(1)
    w = Wnz - loss
    mn = int(w.min())
    return mn, int((w == mn).sum())

rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
budget = float(sys.argv[2]) if len(sys.argv) > 2 else 480
t0 = time.time()
best_overall = (-1, 0)
restart = 0
while time.time() - t0 < budget:
    restart += 1
    S = rng.sample(range(N), DEL)
    cur = score(S)
    stall = 0
    while stall < 3000 and time.time() - t0 < budget:
        i = rng.randrange(DEL)
        newcol = rng.randrange(N)
        if newcol in S: continue
        old = S[i]
        S[i] = newcol
        s2 = score(S)
        # maximize min weight, then minimize count
        better = (s2[0] > cur[0]) or (s2[0] == cur[0] and s2[1] <= cur[1])
        if better:
            if (s2[0] > cur[0]) or s2[1] < cur[1]: stall = 0
            else: stall += 1
            cur = s2
        else:
            S[i] = old
            stall += 1
    if (cur[0], -cur[1]) > (best_overall[0], -best_overall[1]):
        best_overall = cur
        best_S = S[:]
        print(f"restart {restart}: d={cur[0]} (#min={cur[1]})", flush=True)
        if cur[0] >= TARGET:
            print("RECORD?! deleted cols:", sorted(best_S))
            break
print("BEST:", best_overall, "restarts:", restart)
if best_overall[0] >= 45:
    print("deleted cols:", sorted(best_S))
