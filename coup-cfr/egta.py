"""Empirical game-theoretic analysis of 4-player Coup over a parameterized strategy space."""
import random,sys,pickle,itertools,math
from collections import defaultdict
import sweep
from sweep import play, rand_params, NAMES

N=4
BLUFF=[0.0,0.15,0.35,0.60]
CHAL=[(0.0,0.0,0.0),(0.0,0.0,1.0),(0.0,0.35,0.0),(0.0,0.70,0.0),(0.05,0.15,0.0),(0.10,0.35,0.0),(0.20,0.55,0.0)]
def strategy_set(seed=12345,K=None):
    """full grid over bluff frequency x challenge frequency (16 strategies)"""
    S=[]
    for b in BLUFF:
        for cb,cs,k2 in CHAL:
            S.append(dict(b_tax=b,b_steal=b,b_assn=b*0.85,b_bfa=b*0.85,
                          b_bsteal=b,b_bassn=b*1.15,
                          ch_base=cb,ch_slope=cs,ch_k2=k2,pref_steal=0.5,
                          p_exch=0.35,p_fa=0.75))
    return S

def label(i):
    c=CHAL[i%len(CHAL)]
    return f"bluff={BLUFF[i//len(CHAL)]:.2f},chal={c[0]:.2f}/{c[1]:.2f}" + ("+k2" if c[2]>0 else "")

def deal(rng):
    d=[c for c in range(5) for _ in range(3)]; rng.shuffle(d)
    hands=[[d.pop(),d.pop()] for _ in range(N)]
    return hands,d

def profile_payoffs(S,games,seed,shard=0,nshard=1):
    """simulate every multiset profile; return wins/plays keyed (s, sorted others)"""
    rng=random.Random(seed); K=len(S)
    W=defaultdict(int); P=defaultdict(int)
    for pi,prof in enumerate(itertools.combinations_with_replacement(range(K),N)):
        if pi%nshard!=shard: continue
        for _ in range(games):
            seats=list(prof); rng.shuffle(seats)
            par=[S[i] for i in seats]
            hands,deck=deal(rng)
            for rot in range(N):   # duplicate: rotate hands across seats
                hh=[hands[(j+rot)%N] for j in range(N)]
                w,_=play(N,rng,par,(hh,deck))
                for seat in range(N):
                    s=seats[seat]; others=tuple(sorted(seats[:seat]+seats[seat+1:]))
                    P[(s,others)]+=1
                    if w==seat: W[(s,others)]+=1
    return dict(W),dict(P)

def payoff_fn(W,P,K):
    tab={}
    for key,p in P.items():
        tab[key]=W.get(key,0)/p
    def u(s,others): return tab.get((s,tuple(sorted(others))),0.25)
    return u

def replicator(u,K,iters=20000):
    x=[1.0/K]*K
    for t in range(iters):
        exp=[0.0]*K
        for others in itertools.combinations_with_replacement(range(K),N-1):
            # multinomial prob of this unordered triple under x
            cnt=defaultdict(int)
            for o in others: cnt[o]+=1
            coef=math.factorial(N-1)
            for c in cnt.values(): coef//=math.factorial(c)
            pr=coef
            for o in others: pr*=x[o]
            if pr<=0: continue
            for s in range(K): exp[s]+=pr*u(s,others)
        ub=sum(x[s]*exp[s] for s in range(K))
        nx=[max(1e-12,x[s]*(exp[s]/ub if ub>0 else 1.0)) for s in range(K)]
        tot=sum(nx); x=[v/tot for v in nx]
    exp=[0.0]*K
    for others in itertools.combinations_with_replacement(range(K),N-1):
        cnt=defaultdict(int)
        for o in others: cnt[o]+=1
        coef=math.factorial(N-1)
        for c in cnt.values(): coef//=math.factorial(c)
        pr=coef
        for o in others: pr*=x[o]
        for s in range(K): exp[s]+=pr*u(s,others)
    ub=sum(x[s]*exp[s] for s in range(K))
    return x, max(exp)-ub, ub

def equity_at_eq(S,x,games,seed):
    """sample strategies iid from equilibrium mixture; duplicate-rotate hands"""
    rng=random.Random(seed); K=len(S)
    cum=[]; a=0.0
    for v in x: a+=v; cum.append(a)
    def draw():
        r=rng.random()
        for i,c in enumerate(cum):
            if r<c: return i
        return K-1
    deals=[]   # per-deal per-hand win counts, for clustered bootstrap
    for _ in range(games):
        par=[S[draw()] for _ in range(N)]
        hands,deck=deal(rng)
        rec=defaultdict(lambda:[0,0])
        for rot in range(N):
            hh=[hands[(j+rot)%N] for j in range(N)]
            w,_=play(N,rng,par,(hh,deck))
            for seat in range(N):
                h=tuple(sorted(hh[seat])); rec[h][1]+=1
                if w==seat: rec[h][0]+=1
        deals.append({k:tuple(v) for k,v in rec.items()})
    return deals

if __name__=="__main__":
    mode=sys.argv[1]
    S=strategy_set()
    if mode=="payoff":
        W,P=profile_payoffs(S,int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[5]),int(sys.argv[6]))
        pickle.dump((W,P),open(sys.argv[4],"wb")); print("profiles done",len(P))
    elif mode=="eq":
        W,P=pickle.load(open(sys.argv[2],"rb"))
        u=payoff_fn(W,P,len(S)); x,reg,val=replicator(u,len(S))
        pickle.dump(x,open(sys.argv[3],"wb"))
        print("mixture:"); 
        for i,v in enumerate(x):
            if v>1e-4: print(f"   {label(i):32s} {v*100:5.2f}%"); print("eq regret %.5f  value %.4f"%(reg,val))
    elif mode=="equity":
        x=pickle.load(open(sys.argv[2],"rb"))
        d=equity_at_eq(S,x,int(sys.argv[3]),int(sys.argv[4]))
        pickle.dump(d,open(sys.argv[5],"wb")); print("deals",len(d))
