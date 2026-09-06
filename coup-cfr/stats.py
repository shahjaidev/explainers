import pickle,sys,random
from collections import defaultdict
import cfr2
from cfr2 import legal,apply,terminal,infoset,actor,NAMES,CLAIM_ROLE
from eval2 import act,dealcards,mkstate

avg=pickle.load(open(sys.argv[1],"rb")); n=int(sys.argv[2]); rng=random.Random(9)
C=defaultdict(int)
for _ in range(n):
    hands,deck=dealcards(rng); s=mkstate(hands,deck)
    while not terminal(s):
        p=actor(s); a=act(avg,s,rng); ph=s.phase
        if ph=="ACT":
            C["act_total"]+=1; C["act_"+a[0]]+=1
            if a[0] in CLAIM_ROLE:
                C["claims"]+=1
                if CLAIM_ROLE[a[0]] not in s.hands[p]: C["bluff_claims"]+=1; C["bluff_"+a[0]]+=1
                C["claim_"+a[0]]+=1
        elif ph=="RESP":
            A=s.pend[0]; actn=s.pend[1]; C["resp_total"]+=1; C["resp_"+actn]+=1
            if a[0]=="challenge":
                C["chal"]+=1; C["chal_"+actn]+=1
                if CLAIM_ROLE[actn] not in s.hands[A]: C["chal_correct"]+=1
            elif a[0]=="block":
                C["block"]+=1; C["block_"+actn]+=1
                if a[1] not in s.hands[p]: C["block_bluff"]+=1; C["block_bluff_"+actn]+=1
            if actn in CLAIM_ROLE and CLAIM_ROLE[actn] not in s.hands[A]: C["faced_bluff"]+=1
            if actn in CLAIM_ROLE and CLAIM_ROLE[actn] not in s.hands[A] and a[0]=="challenge": C["caught"]+=1
        elif ph=="BLKCH":
            C["blkch_total"]+=1
            if a[0]=="challenge": C["blkch_chal"]+=1
        s=apply(s,a,rng)
    C["games"]+=1; C["plies"]+=s.ply
pct=lambda a,b: f"{100*C[a]/max(1,C[b]):.1f}%"
print("games",C["games"],"avg plies/game %.1f"%(C["plies"]/C["games"]))
print("action mix:",{k[4:]:pct(k,"act_total") for k in sorted(C) if k.startswith("act_") and k!="act_total"})
print("bluff rate among character claims:",pct("bluff_claims","claims"),
      {k[6:]:pct(k,"claim_"+k[6:]) for k in C if k.startswith("bluff_") and k!="bluff_claims"})
print("challenge rate on claims:",pct("chal","resp_total"),{k[5:]:pct(k,"resp_"+k[5:]) for k in C if k.startswith("chal_") and k not in("chal_correct",)})
print("challenge accuracy (claim was a bluff):",pct("chal_correct","chal"))
print("share of bluffs that got challenged:",pct("caught","faced_bluff"))
print("block rate:",pct("block","resp_total"),"of which bluffed:",pct("block_bluff","block"))
print("challenge rate on blocks:",pct("blkch_chal","blkch_total"))
