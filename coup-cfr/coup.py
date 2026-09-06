import random, sys, itertools
from collections import defaultdict

DUKE, ASSASSIN, AMBASSADOR, CAPTAIN, CONTESSA = range(5)
NAMES = ["Duke","Assassin","Ambassador","Captain","Contessa"]
# discard priority: discard the LAST-valuable first
KEEP_VALUE = [5, 3, 2, 4, 3]  # Duke best, Captain, Assassin/Contessa, Ambassador

class G:
    __slots__=("n","hands","coins","deck","revealed","rng")
    def __init__(self,n,rng):
        self.n=n; self.rng=rng
        deck=[c for c in range(5) for _ in range(3)]
        rng.shuffle(deck)
        self.hands=[[deck.pop(),deck.pop()] for _ in range(n)]
        self.deck=deck
        self.coins=[2]*n
        self.revealed=[0]*5

    def alive(self,p): return len(self.hands[p])>0
    def alive_list(self): return [p for p in range(self.n) if self.hands[p]]

    def known(self,p,role):
        return self.revealed[role]+self.hands[p].count(role)

    def lose(self,p):
        h=self.hands[p]
        if not h: return
        # discard the least valuable
        i=min(range(len(h)), key=lambda k: KEEP_VALUE[h[k]])
        c=h.pop(i); self.revealed[c]+=1

    def swap(self,p,role):
        h=self.hands[p]; h.remove(role); self.deck.append(role)
        self.rng.shuffle(self.deck); h.append(self.deck.pop())

    # returns True if claim survives (claimant keeps action)
    def challenge_round(self,claimant,role,audience):
        rng=self.rng
        for ch in audience:
            if ch==claimant or not self.hands[ch]: continue
            k=self.known(ch,role)
            p=0.06+0.30*k
            if k>=3: p=1.0
            if rng.random()<p:
                if role in self.hands[claimant]:
                    self.lose(ch); self.swap(claimant,role); return True
                else:
                    self.lose(claimant); return False
        return True

    def bluff_ok(self,p,role,base):
        k=self.known(p,role)
        if k>=3: return False
        return self.rng.random()<base*(1.0-0.3*k)

def target_pick(g,me):
    opps=[p for p in g.alive_list() if p!=me]
    if not opps: return None
    return max(opps,key=lambda p:(len(g.hands[p]),g.coins[p],g.rng.random()))

def play(n,rng,tracked=None):
    g=G(n,rng)
    start=[tuple(sorted(h)) for h in g.hands]
    turn=0; cur=0
    while True:
        turn+=1
        if turn>400: return None,start
        al=g.alive_list()
        if len(al)==1: return al[0],start
        if not g.hands[cur]:
            cur=(cur+1)%n; continue
        me=cur; h=g.hands[me]; coins=g.coins[me]
        tgt=target_pick(g,me)
        others=[p for p in g.alive_list() if p!=me]
        rng.shuffle(others)

        if coins>=10:
            act="coup"
        elif coins>=3 and (ASSASSIN in h or g.bluff_ok(me,ASSASSIN,0.20)):
            act="assassinate"
        elif coins>=7:
            act="coup"
        elif CAPTAIN in h and tgt is not None and g.coins[tgt]>0:
            act="steal"
        elif DUKE in h:
            act="tax"
        elif AMBASSADOR in h and rng.random()<0.35:
            act="exchange"
        elif g.bluff_ok(me,DUKE,0.30):
            act="tax"
        elif g.bluff_ok(me,CAPTAIN,0.22) and tgt is not None and g.coins[tgt]>0:
            act="steal"
        elif rng.random()<0.75:
            act="foreign_aid"
        else:
            act="income"

        if act=="income":
            g.coins[me]+=1
        elif act=="foreign_aid":
            blocked=False
            for p in others:
                if DUKE in g.hands[p] or g.bluff_ok(p,DUKE,0.18):
                    if g.challenge_round(p,DUKE,[me]):
                        blocked=True
                    break
            if not blocked: g.coins[me]+=2
        elif act=="tax":
            if g.challenge_round(me,DUKE,others): g.coins[me]+=3
        elif act=="steal":
            if tgt is not None and g.challenge_round(me,CAPTAIN,others):
                blk=None
                for r in (CAPTAIN,AMBASSADOR):
                    if r in g.hands[tgt]: blk=r; break
                if blk is None and g.bluff_ok(tgt,CAPTAIN,0.30): blk=CAPTAIN
                ok=True
                if blk is not None:
                    ok = not g.challenge_round(tgt,blk,[me])
                if ok:
                    amt=min(2,g.coins[tgt]); g.coins[tgt]-=amt; g.coins[me]+=amt
        elif act=="exchange":
            if g.challenge_round(me,AMBASSADOR,others):
                pool=h[:]+[g.deck.pop(),g.deck.pop()]
                pool.sort(key=lambda c:-KEEP_VALUE[c])
                g.hands[me]=pool[:len(h)]
                g.deck.extend(pool[len(h):]); rng.shuffle(g.deck)
        elif act=="assassinate":
            if tgt is None: g.coins[me]+=1
            else:
                g.coins[me]-=3
                if g.challenge_round(me,ASSASSIN,others):
                    blk = CONTESSA in g.hands[tgt]
                    if not blk:
                        pb = 0.85 if len(g.hands[tgt])==1 else 0.40
                        blk = g.bluff_ok(tgt,CONTESSA,pb)
                    if blk:
                        if not g.challenge_round(tgt,CONTESSA,[me]):
                            g.lose(tgt)
                    else:
                        g.lose(tgt)
        elif act=="coup":
            if tgt is not None:
                g.coins[me]-=7; g.lose(tgt)
        cur=(cur+1)%n

def run(seed,games,n):
    rng=random.Random(seed)
    wins=defaultdict(int); plays=defaultdict(int)
    draws=0
    for _ in range(games):
        w,start=play(n,rng)
        for i,s in enumerate(start):
            plays[s]+=1
            if w==i: wins[s]+=1
        if w is None: draws+=1
    return dict(wins),dict(plays),draws

if __name__=="__main__":
    seed=int(sys.argv[1]); games=int(sys.argv[2]); n=int(sys.argv[3])
    import pickle
    pickle.dump(run(seed,games,n),open(sys.argv[4],"wb"))
