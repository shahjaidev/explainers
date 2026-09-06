"""Best response v2: greedy-on-regret responder with a safe fallback at unvisited infosets."""
import pickle,sys,random
import cfr2
from cfr2 import legal,apply,terminal,infoset,actor
KEEP_VALUE=[5,3,2,4,3]
from eval2 import act,dealcards,mkstate

def safe(s):
    acts=legal(s); ph=s.phase
    if ph=="ACT":
        c=s.coins[actor(s)]
        for a in acts:
            if a[0]=="coup" and c>=7: return a
        return ("income",)
    if ph in ("RESP","BLKCH"): return ("pass",)
    if ph=="LOSE": return min(acts,key=lambda a:KEEP_VALUE[a[1]])
    if ph=="EXCH": return max(acts,key=lambda a:sum(KEEP_VALUE[c] for c in a[1:]))
    return acts[0]

def make_policy(tree):
    def pol(s,rng):
        acts=legal(s); nd=tree.get(infoset(s))
        if nd is None or nd.n!=len(acts) or max(nd.r)<=0: return safe(s)
        return acts[max(range(nd.n),key=lambda j:nd.r[j])]
    return pol

def play(polA,polB,st,rng):
    s=st
    while not terminal(s):
        p=actor(s); s=apply(s,(polA if p==0 else polB)(s,rng),rng)
    return s.winner if s.done else None

if __name__=="__main__":
    fixed=pickle.load(open(sys.argv[1],"rb")); iters=int(sys.argv[2]); seed=int(sys.argv[3])
    tree=cfr2.train(iters,seed,fixed=fixed); cfr2.FIXED[0]=None
    br=make_policy(tree)
    fx=lambda s,rng: act(fixed,s,rng)
    rng=random.Random(seed+7); win=n=0
    for _ in range(50000):
        hands,deck=dealcards(rng)
        for swap in (0,1):
            hh=[hands[1],hands[0]] if swap else hands
            for seat in (0,1):
                r=play(br,fx,mkstate(hh,deck),rng) if seat==0 else play(fx,br,mkstate(hh,deck),rng)
                n+=1; win+= (r==seat)
    v=win/n
    print(f"greedy best-responder win rate vs fixed (seat-balanced, 200k games): {v*100:.2f}%")
    print(f"exploitability lower bound (win=+1/lose=-1): {2*(v-0.5):+.4f}")
