# Coup at Equilibrium — simulation code

Companion scripts for `../coup-cfr.html`. Pure Python 3.11, no dependencies.

| Script | Purpose |
|---|---|
| `coup.py` | Scripted-agent simulator, 3–5 players, bot v1 (no block memory). `python3 coup.py SEED GAMES NPLAYERS OUT.pkl` |
| `coup3.py` | Scripted simulator with block memory and bluffing modes. Last arg: `0` baseline, `1` fully honest, `2` no bluffs but challenges. |
| `sweep.py` | Per-seat randomized parameters; also exposes `play()` with preset deals for `egta.py`. |
| `cfr.py` | Heads-up engine + outcome-sampling MCCFR. `python3 cfr.py ITERS SEED OUT.pkl` |
| `cfr2.py` | Same engine with CFR+ regret clamping and linear averaging; also supports a frozen opponent for best-response training. |
| `evalcfr.py` | Plain self-play evaluation (seat-confounded; superseded by `eval2.py`). |
| `eval2.py` | Duplicate-scored evaluation with clustered bootstrap CIs. `python3 eval2.py A.pkl[,B.pkl] NDEALS SEED` |
| `br.py`, `br2.py` | Best-response training against a frozen strategy (average-strategy and greedy responders). |
| `egta.py` | Strategy grid, payoff estimation (`payoff`), replicator dynamics (`eq`), hand equity at equilibrium (`equity`). |
| `stats.py` | Behavioural statistics of a strategy in self-play. |

Seeds and iteration counts for every reported number are in Section 7 of the paper.
