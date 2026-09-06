"""Outcome-sampling MCCFR for 2-player Coup."""
import random, sys, pickle
from collections import defaultdict

DUKE, ASSASSIN, AMBASSADOR, CAPTAIN, CONTESSA = range(5)
NAMES = ["Duke","Assassin","Ambassador","Captain","Contessa"]
MAXPLY = 160

class S:
    __slots__=("hands","coins","deck","rev","cur","phase","pend","cont","ply","claims","done","winner")
    def __init__(self): pass
    def copy(self):
        t=S(); t.hands=[self.hands[0][:],self.hands[1][:]]; t.coins=self.coins[:]
        t.deck=self.deck[:]; t.rev=self.rev[:]; t.cur=self.cur; t.phase=self.phase
        t.pend=self.pend; t.cont=self.cont; t.ply=self.ply
        t.claims=[self.claims[0][:],self.claims[1][:]]; t.done=self.done; t.winner=self.winner
        return t

def deal(rng):
    d=[c for c in range(5) for _ in range(3)]; rng.shuffle(d)
    s=S(); s.hands=[[d.pop(),d.pop()],[d.pop(),d.pop()]]; s.coins=[2,2]
    s.deck=d; s.rev=[0]*5; s.cur=0; s.phase="ACT"; s.pend=None; s.cont=None
    s.ply=0; s.claims=[[0]*5,[0]*5]; s.done=False; s.winner=None
    return s

def draw(s,rng):
    i=rng.randrange(len(s.deck)); return s.deck.pop(i)

# ---------- who acts, and legal actions ----------
def actor(s):
    ph=s.phase
    if ph=="ACT": return s.cur
    if ph=="RESP": return 1-s.pend[0]
    if ph=="BLKCH": return s.pend[0]
    if ph=="LOSE": return s.pend[0]
    if ph=="EXCH": return s.pend[0]
    raise AssertionError(ph)

def legal(s):
    ph=s.phase; p=actor(s)
    if ph=="ACT":
        c=s.coins[p]
        if c>=10: return [("coup",)]
        a=[("income",),("foreign_aid",),("tax",),("exchange",)]
        if s.coins[1-p]>0: a.append(("steal",))
        if c>=3: a.append(("assassinate",))
        if c>=7: a.append(("coup",))
        return a
    if ph=="RESP":
        act=s.pend[1]
        if act=="foreign_aid": return [("pass",),("block",DUKE)]
        if act=="tax" or act=="exchange": return [("pass",),("challenge",)]
        if act=="steal": return [("pass",),("challenge",),("block",CAPTAIN),("block",AMBASSADOR)]
        if act=="assassinate": return [("pass",),("challenge",),("block",CONTESSA)]
    if ph=="BLKCH": return [("pass",),("challenge",)]
    if ph=="LOSE":
        h=s.hands[p]
        return [("discard",c) for c in sorted(set(h))]
    if ph=="EXCH":
        pool=s.pend[2]; k=s.pend[3]
        opts=sorted(set(tuple(sorted(x)) for x in _combs(pool,k)))
        return [("keep",)+o for o in opts]
    raise AssertionError(ph)

def _combs(pool,k):
    import itertools
    return itertools.combinations(sorted(pool),k)

CLAIM_ROLE={"tax":DUKE,"steal":CAPTAIN,"assassinate":ASSASSIN,"exchange":AMBASSADOR}

CB=[0,1,2,3,4,4,4,5,5,5,6,6,6,6]
def cb(c): return CB[c] if c<len(CB) else 6
def infoset(s):
    p=actor(s); ph=s.phase
    key=(ph,tuple(sorted(s.hands[p])),cb(s.coins[p]),cb(s.coins[1-p]),
         len(s.hands[1-p]),tuple(s.rev),tuple(s.claims[1-p]))
    if ph in ("RESP","BLKCH"): key+=(s.pend[1],s.pend[2] if ph=="BLKCH" else None)
    if ph=="EXCH": key+=(tuple(sorted(s.pend[2])),)
    if ph=="LOSE": key+=(s.cont[0] if s.cont else None,)
    return key

# ---------- transitions ----------
def lose_card(s,p,cont):
    if len(s.hands[p])==1:
        c=s.hands[p][0]; s.hands[p]=[]; s.rev[c]+=1
        s.done=True; s.winner=1-p; return
    s.phase="LOSE"; s.pend=(p,); s.cont=cont

def swap_card(s,p,role,rng):
    s.hands[p].remove(role); s.deck.append(role); s.hands[p].append(draw(s,rng))

def end_turn(s):
    s.phase="ACT"; s.pend=None; s.cont=None; s.cur=1-s.cur; s.ply+=1

def resolve(s,tag,rng):
    """apply the successful action named by tag"""
    kind=tag[0]
    if kind=="tax": s.coins[tag[1]]+=3; end_turn(s)
    elif kind=="fa": s.coins[tag[1]]+=2; end_turn(s)
    elif kind=="steal":
        a,d=tag[1],tag[2]; amt=min(2,s.coins[d]); s.coins[d]-=amt; s.coins[a]+=amt; end_turn(s)
    elif kind=="assn":
        lose_card(s,tag[1],("none",))
        if s.phase!="LOSE" and not s.done: end_turn(s)
    elif kind=="exch":
        p=tag[1]; k=len(s.hands[p]); pool=s.hands[p]+[draw(s,rng),draw(s,rng)]
        s.phase="EXCH"; s.pend=(p,None,pool,k); s.cont=None
    elif kind=="none": end_turn(s)
    else: raise AssertionError(kind)

def apply(s,a,rng):
    s=s.copy(); ph=s.phase; p=actor(s)
    if ph=="ACT":
        act=a[0]; o=1-p
        if act=="income": s.coins[p]+=1; end_turn(s)
        elif act=="coup":
            s.coins[p]-=7; lose_card(s,o,("none",))
            if s.phase!="LOSE" and not s.done: end_turn(s)
        elif act=="foreign_aid":
            s.phase="RESP"; s.pend=(p,"foreign_aid",None)
        else:
            if act=="assassinate": s.coins[p]-=3
            s.claims[p][CLAIM_ROLE[act]]=1
            s.phase="RESP"; s.pend=(p,act,None)
        return s
    if ph=="RESP":
        A=s.pend[0]; act=s.pend[1]; R=p
        if a[0]=="pass":
            if act=="foreign_aid": resolve(s,("fa",A),rng)
            elif act=="tax": resolve(s,("tax",A),rng)
            elif act=="steal": resolve(s,("steal",A,R),rng)
            elif act=="assassinate": resolve(s,("assn",R),rng)
            elif act=="exchange": resolve(s,("exch",A),rng)
            return s
        if a[0]=="challenge":
            role=CLAIM_ROLE[act]
            tag={"tax":("tax",A),"steal":("steal",A,R),"assassinate":("assn",R),
                 "exchange":("exch",A)}[act]
            if role in s.hands[A]:
                swap_card(s,A,role,rng); lose_card(s,R,tag)
                if s.phase!="LOSE" and not s.done: resolve(s,tag,rng)
            else:
                lose_card(s,A,("none",))
                if s.phase!="LOSE" and not s.done: end_turn(s)
            return s
        # block
        role=a[1]; s.claims[R][role]=1
        s.phase="BLKCH"; s.pend=(A,act,role); s.cont=None
        return s
    if ph=="BLKCH":
        A=s.pend[0]; act=s.pend[1]; role=s.pend[2]; B=1-A
        if a[0]=="pass": end_turn(s); return s
        if role in s.hands[B]:
            swap_card(s,B,role,rng); lose_card(s,A,("none",))
            if s.phase!="LOSE" and not s.done: end_turn(s)
        else:
            tag={"foreign_aid":("fa",A),"steal":("steal",A,B),"assassinate":("assn",B)}[act]
            lose_card(s,B,tag)
            if s.phase!="LOSE" and not s.done: resolve(s,tag,rng)
        return s
    if ph=="LOSE":
        c=a[1]; s.hands[p].remove(c); s.rev[c]+=1
        cont=s.cont; s.cont=None; s.pend=None
        if not s.hands[p]: s.done=True; s.winner=1-p; return s
        if cont and cont[0]!="none": resolve(s,cont,rng)
        else: end_turn(s)
        return s
    if ph=="EXCH":
        keep=list(a[1:]); pool=list(s.pend[2])
        for c in keep: pool.remove(c)
        s.hands[p]=keep; s.deck.extend(pool)
        end_turn(s); return s
    raise AssertionError(ph)

def terminal(s):
    if s.done: return True
    return s.ply>MAXPLY

def util(s,i):
    if s.done: return 1.0 if s.winner==i else -1.0
    return 0.0

# ---------- MCCFR ----------
EPS=0.6
class Node:
    __slots__=("r","sm","n")
    def __init__(self,n): self.r=[0.0]*n; self.sm=[0.0]*n; self.n=n
    def strat(self):
        pos=[x if x>0 else 0.0 for x in self.r]; t=sum(pos)
        if t<=0: return [1.0/self.n]*self.n
        return [x/t for x in pos]

ITER=[1]
FIXED=[None]   # if set, opponent plays this fixed average strategy (best-response mode)

def os_cfr(s,i,pi_i,pi_o,samp,tree,rng):
    if terminal(s): return util(s,i)/samp, 1.0
    p=actor(s); acts=legal(s); n=len(acts)
    I=infoset(s)
    if p!=i and FIXED[0] is not None:
        pr=FIXED[0].get(I)
        sig=pr if (pr is not None and len(pr)==n) else [1.0/n]*n
        nd=None
    else:
        nd=tree.get(I)
        if nd is None or nd.n!=n:
            nd=Node(n); tree[I]=nd
        sig=nd.strat()
    if p==i:
        sp=[EPS/n+(1-EPS)*x for x in sig]
    else:
        sp=sig
    x=rng.random(); acc=0.0; k=n-1
    for j in range(n):
        acc+=sp[j]
        if x<acc: k=j; break
    a=acts[k]
    ns=apply(s,a,rng)
    if p==i:
        u,tail=os_cfr(ns,i,pi_i*sig[k],pi_o,samp*sp[k],tree,rng)
        W=u*pi_o
        r=nd.r; base=W*tail
        for j in range(n):
            d=(base-base*sig[k]) if j==k else (-base*sig[k])
            v=r[j]+d
            r[j]= v if v>0 else 0.0
        return u, tail*sig[k]
    else:
        u,tail=os_cfr(ns,i,pi_i,pi_o*sig[k],samp*sp[k],tree,rng)
        if nd is not None:
            sm=nd.sm; w=(pi_i/samp)*ITER[0]
            for j in range(n): sm[j]+=w*sig[j]
        return u, tail*sig[k]

def train(iters,seed,fixed=None,only=None):
    FIXED[0]=fixed
    rng=random.Random(seed); tree={}
    for t in range(iters):
        ITER[0]=t+1
        for i in ((0,1) if only is None else (only,)):
            s=deal(rng)
            os_cfr(s,i,1.0,1.0,1.0,tree,rng)
    return tree

if __name__=="__main__":
    sys.setrecursionlimit(100000)
    iters=int(sys.argv[1]); seed=int(sys.argv[2]); out=sys.argv[3]
    tr=train(iters,seed)
    avg={}
    for I,nd in tr.items():
        t=sum(nd.sm)
        avg[I]=[x/t for x in nd.sm] if t>0 else [1.0/nd.n]*nd.n
    pickle.dump(avg,open(out,"wb"))
    print("infosets",len(tr))
