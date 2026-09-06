"""Exploitability lower bound: train a best responder against a fixed strategy."""
import pickle,sys,random
import cfr2
from eval2 import duplicate

if __name__=="__main__":
    fixed=pickle.load(open(sys.argv[1],"rb"))
    iters=int(sys.argv[2]); seed=int(sys.argv[3])
    tr=cfr2.train(iters,seed,fixed=fixed)
    br={}
    for I,nd in tr.items():
        t=sum(nd.sm)
        br[I]=[x/t for x in nd.sm] if t>0 else [1.0/nd.n]*nd.n
    cfr2.FIXED[0]=None
    pickle.dump(br,open(sys.argv[4],"wb"))
    deals,_=duplicate([br,fixed],40000,seed+1)
    w=p=0
    # responder is seat 0 in game 1 and seat 1 in game 2 of each duplicate pair
    import collections
    rng=random.Random(seed)
    # recompute directly: play responder vs fixed in both seats
    from eval2 import dealcards,mkstate,one
    rng=random.Random(seed+7); win=0; n=0
    for _ in range(40000):
        hands,deck=dealcards(rng)
        for swap in (0,1):
            hh=[hands[1],hands[0]] if swap else hands
            for seat in (0,1):
                avgs=[br,fixed] if seat==0 else [fixed,br]
                r=one(avgs,mkstate(hh,deck),rng)
                n+=1
                if r==seat: win+=1
    v=win/n
    print(f"best-responder win rate vs fixed strategy (seat-balanced): {v*100:.2f}%")
    print(f"exploitability lower bound (utility units, win=+1/lose=-1): {2*(v-0.5):+.4f}")
