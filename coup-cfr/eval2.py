"""Duplicate (seat-swapped) evaluation of heads-up Coup strategies + clustered bootstrap CIs."""
import random,pickle,sys,math
from collections import defaultdict
import cfr2
from cfr2 import S,legal,apply,terminal,infoset,actor,NAMES

def mkstate(hands,deck):
    s=S(); s.hands=[hands[0][:],hands[1][:]]; s.coins=[2,2]; s.deck=deck[:]
    s.rev=[0]*5; s.cur=0; s.phase="ACT"; s.pend=None; s.cont=None
    s.ply=0; s.claims=[[0]*5,[0]*5]; s.done=False; s.winner=None
    return s

def dealcards(rng):
    d=[c for c in range(5) for _ in range(3)]; rng.shuffle(d)
    return [[d.pop(),d.pop()],[d.pop(),d.pop()]], d

def act(avg,s,rng):
    acts=legal(s); pr=avg.get(infoset(s))
    if pr is None or len(pr)!=len(acts): return acts[rng.randrange(len(acts))]
    x=rng.random(); a=0.0
    for j,q in enumerate(pr):
        a+=q
        if x<a: return acts[j]
    return acts[-1]

def one(avgs,st,rng):
    s=st
    while not terminal(s): s=apply(s,act(avgs[actor(s)],s,rng),rng)
    return s.winner if s.done else None

def duplicate(avgs,ndeals,seed):
    """each deal played twice with seats swapped -> removes first-player bias"""
    rng=random.Random(seed); deals=[]; p0=0; tot=0
    for _ in range(ndeals):
        hands,deck=dealcards(rng)
        rec=defaultdict(lambda:[0,0])
        for swap in (0,1):
            hh=[hands[1],hands[0]] if swap else hands
            w=one(avgs,mkstate(hh,deck),rng)
            for seat in (0,1):
                h=tuple(sorted(hh[seat])); rec[h][1]+=1
                if w==seat: rec[h][0]+=1
            if w==0: p0+=1
            tot+=1
        deals.append({k:tuple(v) for k,v in rec.items()})
    return deals,p0/tot

def summarize(deals,label,B=400,seed=5):
    W=defaultdict(int); P=defaultdict(int)
    for d in deals:
        for k,(w,p) in d.items(): W[k]+=w; P[k]+=p
    rng=random.Random(seed); n=len(deals)
    boot=defaultdict(list)
    idx=range(n)
    for b in range(B):
        bw=defaultdict(int); bp=defaultdict(int)
        for _ in range(n):
            d=deals[rng.randrange(n)]
            for k,(w,p) in d.items(): bw[k]+=w; bp[k]+=p
        for k in bp: boot[k].append(bw[k]/bp[k])
    rows=[]
    for k in P:
        v=sorted(boot[k]); lo=v[int(.025*len(v))]; hi=v[int(.975*len(v))-1]
        rows.append((W[k]/P[k],lo,hi,k,P[k]))
    rows.sort(reverse=True)
    print(label)
    for r,lo,hi,k,p in rows:
        print(f"{' + '.join(NAMES[c] for c in k):26s} {r*100:6.2f}%  95%CI [{lo*100:5.2f},{hi*100:5.2f}]  n={p}")
    return {k:r for r,lo,hi,k,p in rows}

if __name__=="__main__":
    files=sys.argv[1].split(","); nd=int(sys.argv[2]); seed=int(sys.argv[3])
    avgs=[pickle.load(open(f,"rb")) for f in files]
    if len(avgs)==1: avgs=avgs*2
    deals,p0=duplicate(avgs,nd,seed)
    print(f"deals={nd} games={nd*2} first-player win rate={p0*100:.2f}%")
    summarize(deals,"duplicate-scored hand equity (clustered bootstrap over deals)")
