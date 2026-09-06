import random,pickle,sys,math
from collections import defaultdict
import cfr2 as cfr
from cfr2 import deal,legal,apply,terminal,infoset,actor,NAMES

def pick(avg,s,rng,fallback=None):
    acts=legal(s); I=infoset(s); pr=avg.get(I)
    if pr is None or len(pr)!=len(acts):
        return acts[rng.randrange(len(acts))]
    x=rng.random(); acc=0.0
    for j,q in enumerate(pr):
        acc+=q
        if x<acc: return acts[j]
    return acts[-1]

def game(avgs,rng):
    s=deal(rng); start=[tuple(sorted(h)) for h in s.hands]
    while not terminal(s):
        p=actor(s); s=apply(s,pick(avgs[p],s,rng),rng)
    return (s.winner if s.done else None), start

def run(avgs,n,seed):
    rng=random.Random(seed); W=defaultdict(int); P=defaultdict(int); dr=0
    seat=[0,0]
    for _ in range(n):
        w,st=game(avgs,rng)
        for i,h in enumerate(st):
            P[h]+=1
            if w==i: W[h]+=1
        if w is None: dr+=1
        else: seat[w]+=1
    return W,P,dr,seat

if __name__=="__main__":
    files=sys.argv[1].split(","); n=int(sys.argv[2]); seed=int(sys.argv[3])
    avgs=[pickle.load(open(f,"rb")) for f in files]
    if len(avgs)==1: avgs=avgs*2
    W,P,dr,seat=run(avgs,n,seed)
    rows=sorted(((W[k]/v,k,v) for k,v in P.items()),reverse=True)
    print(f"games={n} draws={dr} seatwins={seat}")
    for r,k,v in rows:
        se=math.sqrt(r*(1-r)/v)
        print(f"{' + '.join(NAMES[c] for c in k):26s} {r*100:6.2f}%  ci±{se*196:.2f}  n={v}")
