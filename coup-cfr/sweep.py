"""4-player Coup with per-seat randomized bot parameters (robustness sweep)."""
import random,sys,pickle,math
from collections import defaultdict
DUKE,ASSASSIN,AMBASSADOR,CAPTAIN,CONTESSA=range(5)
NAMES=["Duke","Assassin","Ambassador","Captain","Contessa"]
KEEP=[5,3,2,4,3]

def rand_params(rng):
    return dict(
        b_tax=rng.uniform(0,0.6), b_steal=rng.uniform(0,0.6), b_assn=rng.uniform(0,0.5),
        b_bfa=rng.uniform(0,0.5), b_bsteal=rng.uniform(0,0.6), b_bassn=rng.uniform(0,0.7),
        ch_base=rng.uniform(0,0.20), ch_slope=rng.uniform(0,0.60),
        pref_steal=rng.random(), p_exch=rng.uniform(0,0.7), p_fa=rng.uniform(0.3,1.0))

class G:
    def __init__(self,n,rng,par,preset=None):
        self.n=n; self.rng=rng; self.par=par
        if preset is None:
            d=[c for c in range(5) for _ in range(3)]; rng.shuffle(d)
            self.hands=[[d.pop(),d.pop()] for _ in range(n)]
            self.deck=d
        else:
            hands,deck=preset
            self.hands=[h[:] for h in hands]; self.deck=deck[:]; self.coins=[2]*n; self.rev=[0]*5
        self.no_ass=set(); self.no_steal=set()
    def alive(self): return [p for p in range(self.n) if self.hands[p]]
    def known(self,p,r): return self.rev[r]+self.hands[p].count(r)
    def lose(self,p):
        h=self.hands[p]
        if not h: return
        i=min(range(len(h)),key=lambda k:KEEP[h[k]])
        c=h.pop(i); self.rev[c]+=1
        self.no_ass.discard(p); self.no_steal.discard(p)
    def swap(self,p,r):
        self.hands[p].remove(r); self.deck.append(r)
        self.rng.shuffle(self.deck); self.hands[p].append(self.deck.pop())
    def chal(self,claimant,role,aud):
        for ch in aud:
            if ch==claimant or not self.hands[ch]: continue
            k=self.known(ch,role); pr=self.par[ch]
            p=pr["ch_base"]+pr["ch_slope"]*k
            if k>=2: p=max(p,pr.get("ch_k2",0.0))
            if k>=3: p=1.0
            if self.rng.random()<p:
                if role in self.hands[claimant]:
                    self.lose(ch); self.swap(claimant,role); return True
                self.lose(claimant); return False
        return True
    def bluff(self,p,role,key,mult=1.0):
        k=self.known(p,role)
        if k>=3: return False
        base=min(1.0,self.par[p][key]*mult)
        return self.rng.random()<base*(1.0-0.3*k)

def tpick(g,me,skip=None):
    o=[p for p in g.alive() if p!=me and (skip is None or p not in skip)]
    if not o: return None
    return max(o,key=lambda p:(len(g.hands[p]),g.coins[p],g.rng.random()))

def play(n,rng,par,preset=None):
    g=G(n,rng,par,preset); start=[tuple(sorted(h)) for h in g.hands]; cur=0; turn=0
    while True:
        turn+=1
        if turn>2000: return None,start
        al=g.alive()
        if len(al)==1: return al[0],start
        if not g.hands[cur]: cur=(cur+1)%n; continue
        me=cur; h=g.hands[me]; c=g.coins[me]; P=par[me]
        tgt=tpick(g,me); tga=tpick(g,me,g.no_ass); tgs=tpick(g,me,g.no_steal)
        if tgs is not None and g.coins[tgs]==0: tgs=None
        others=[p for p in g.alive() if p!=me]; rng.shuffle(others)
        steal_ok = CAPTAIN in h and tgs is not None
        tax_ok = DUKE in h
        if c>=10: act="coup"
        elif c>=3 and tga is not None and (ASSASSIN in h or g.bluff(me,ASSASSIN,"b_assn")): act="assassinate"
        elif c>=7: act="coup"
        elif steal_ok and tax_ok: act="steal" if rng.random()<P["pref_steal"] else "tax"
        elif steal_ok: act="steal"
        elif tax_ok: act="tax"
        elif AMBASSADOR in h and rng.random()<P["p_exch"]: act="exchange"
        elif g.bluff(me,DUKE,"b_tax"): act="tax"
        elif g.bluff(me,CAPTAIN,"b_steal") and tgs is not None: act="steal"
        elif rng.random()<P["p_fa"]: act="foreign_aid"
        else: act="income"

        if act=="income": g.coins[me]+=1
        elif act=="foreign_aid":
            blk=False
            for p in others:
                if DUKE in g.hands[p] or g.bluff(p,DUKE,"b_bfa"):
                    if g.chal(p,DUKE,[me]): blk=True
                    break
            if not blk: g.coins[me]+=2
        elif act=="tax":
            if g.chal(me,DUKE,others): g.coins[me]+=3
        elif act=="steal":
            t=tgs
            if t is not None and g.chal(me,CAPTAIN,others):
                b=None
                for r in (CAPTAIN,AMBASSADOR):
                    if r in g.hands[t]: b=r; break
                if b is None and g.bluff(t,CAPTAIN,"b_bsteal"): b=CAPTAIN
                ok=True
                if b is not None:
                    ok=not g.chal(t,b,[me])
                    if not ok: g.no_steal.add(t)
                if ok:
                    a=min(2,g.coins[t]); g.coins[t]-=a; g.coins[me]+=a
        elif act=="exchange":
            if g.chal(me,AMBASSADOR,others):
                pool=h[:]+[g.deck.pop(),g.deck.pop()]
                pool.sort(key=lambda x:-KEEP[x])
                g.hands[me]=pool[:len(h)]; g.deck.extend(pool[len(h):]); rng.shuffle(g.deck)
        elif act=="assassinate":
            t=tga
            if t is None: g.coins[me]+=1
            else:
                g.coins[me]-=3
                if g.chal(me,ASSASSIN,others):
                    b=CONTESSA in g.hands[t]
                    if not b:
                        m=2.0 if len(g.hands[t])==1 else 1.0
                        b=g.bluff(t,CONTESSA,"b_bassn",m)
                    if b:
                        if not g.chal(t,CONTESSA,[me]): g.lose(t)
                        else: g.no_ass.add(t)
                    else: g.lose(t)
        elif act=="coup":
            if tgt is not None: g.coins[me]-=7; g.lose(tgt)
        cur=(cur+1)%n

def run(seed,games,n):
    rng=random.Random(seed)
    W=defaultdict(int); P=defaultdict(int); dr=0
    # regime split: by mean bluff level at the table
    RW=defaultdict(int); RP=defaultdict(int)
    for _ in range(games):
        par=[rand_params(rng) for _ in range(n)]
        mb=sum(p["b_tax"]+p["b_steal"]+p["b_assn"]+p["b_bfa"]+p["b_bsteal"]+p["b_bassn"] for p in par)/(6*n)
        reg=0 if mb<0.2 else (1 if mb<0.3 else 2)
        w,st=play(n,rng,par)
        for i,hh in enumerate(st):
            P[hh]+=1; RP[(reg,hh)]+=1
            if w==i: W[hh]+=1; RW[(reg,hh)]+=1
        if w is None: dr+=1
    return dict(W),dict(P),dr,dict(RW),dict(RP)

if __name__=="__main__":
    seed=int(sys.argv[1]); games=int(sys.argv[2]); n=int(sys.argv[3])
    pickle.dump(run(seed,games,n),open(sys.argv[4],"wb"))
