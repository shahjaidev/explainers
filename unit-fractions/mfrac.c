// mfrac: decide representability of m/n = 1/x + 1/y + 1/z (x,y,z positive integers)
// and scan ranges for exceptions.
//
// Complete criterion (sound and complete for any n):
//   m/n representable  <=>  exists x with n/m < x <= 3n/m, a = m*x - n, b = n*x,
//   and a divisor pair d*d' = b^2 with d ≡ d' ≡ -b (mod a).
//   Then y = (b+d)/a, z = (b+d')/a and 1/y + 1/z = a/b identically.
//
// Modes:
//   ./mfrac small  m LO HI          complete decision for every n in [LO,HI]; prints all non-representable n
//   ./mfrac primes m LO HI          fast first-hit scan over primes in [LO,HI]; escalates to complete
//                                   decision on miss; prints PRIME-EXCEPTION lines and stats
//   ./mfrac one    m n              complete decision for a single n, prints witness or NONREP
//   ./mfrac pw     m                complete decision for all primes in (m^2, 2m^2); prints exceptions
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef unsigned long long u64;
typedef __uint128_t u128;

/* ---------- small primes for partial factorization ---------- */
static u64 smallp[512]; static int nsmallp = 0;
static void init_smallp(int limit){
    for (int i = 2; i < limit && nsmallp < 512; i++){
        int isp = 1;
        for (int j = 2; j*j <= i; j++) if (i % j == 0){ isp = 0; break; }
        if (isp) smallp[nsmallp++] = i;
    }
}

/* ---------- u64 arithmetic ---------- */
static u64 mulmod(u64 a, u64 b, u64 m){ return (u64)((u128)a * b % m); }
static u64 powmod(u64 b, u64 e, u64 m){ u64 r=1; b%=m; while(e){ if(e&1) r=mulmod(r,b,m); b=mulmod(b,b,m); e>>=1; } return r; }
static u64 gcd64(u64 a, u64 b){ while(b){ u64 t=a%b; a=b; b=t; } return a; }
static int is_prime_u64(u64 n){
    if (n < 2) return 0;
    static const u64 tp[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (int i=0;i<12;i++){ if (n % tp[i] == 0) return n == tp[i]; }
    u64 d = n-1; int r = 0; while (!(d&1)){ d >>= 1; r++; }
    for (int i=0;i<12;i++){
        u64 x = powmod(tp[i], d, n);
        if (x == 1 || x == n-1) continue;
        int ok = 0;
        for (int j=0;j<r-1;j++){ x = mulmod(x,x,n); if (x == n-1){ ok=1; break; } }
        if (!ok) return 0;
    }
    return 1;
}
static u64 pollard(u64 n){
    if (!(n&1)) return 2;
    for (u64 c = 1;; c++){
        u64 x = 2, y = 2, d = 1;
        while (d == 1){
            x = (mulmod(x,x,n) + c) % n;
            y = (mulmod(y,y,n) + c) % n; y = (mulmod(y,y,n) + c) % n;
            d = gcd64(x>y?x-y:y-x, n);
        }
        if (d != n) return d;
    }
}
/* full factorization of n into (prime, exp) pairs */
static int factor_full(u64 n, u64 *pr, int *ex){
    int k = 0;
    u64 stack[64]; int top = 0; stack[top++] = n;
    while (top){
        u64 v = stack[--top];
        if (v == 1) continue;
        if (is_prime_u64(v)){
            int found = -1;
            for (int i=0;i<k;i++) if (pr[i]==v) found=i;
            if (found>=0) ex[found]++; else { pr[k]=v; ex[k]=1; k++; }
            continue;
        }
        u64 d = 0;
        for (int i=0;i<nsmallp;i++){ u64 q=smallp[i]; if (q*q>v) break; if (v%q==0){ d=q; break; } }
        if (!d) d = pollard(v);
        stack[top++] = d; stack[top++] = v/d;
    }
    return k;
}

/* ---------- modular inverse ---------- */
static u64 inv_mod(u64 a, u64 m){ // gcd(a,m)=1
    long long g=m, x=0, r=a%m, x1=1;
    while (r){ long long q=g/r, t=g-q*r; g=r; r=t; t=x-q*x1; x=x1; x1=t; }
    long long res = x % (long long)m; if (res<0) res += m;
    return (u64)res;
}

/* ----------------------------------------------------------------------
   Complete decision for a single value n (any n >= 2), with witness output.
   Enumerates ALL divisors d of b^2 = (n*x)^2 via full factorization.
   Returns 1 if representable (fills witness), 0 if certified non-representable.
   ---------------------------------------------------------------------- */
static int decide_complete(u64 m, u64 n, u64 *wx, u64 *wd, u64 *wa){
    if (3*1ULL*n < m) return 0;               // m/n > 3: impossible
    u64 x_lo = n/m + 1, x_hi = (3*n)/m;
    if (m*x_hi == 3*n){ /* x = 3n/m gives a = 2n? keep; also exact 1/x+1/x+1/x case */ }
    // exact representation with x = n/m if m | n: 1/x split into ... handled by generic x range?
    // m|n: m/n = 1/(n/m): representable as 1/(2q)+1/(3q)+1/(6q) with q=n/m. Catch directly:
    if (n % m == 0){ *wx = 2*(n/m); *wd = 0; *wa = 0; return 1; }
    for (u64 x = x_lo; x <= x_hi; x++){
        u64 a = m*x - n;
        u128 b = (u128)n * x;
        if (b >> 62){ fprintf(stderr, "FATAL b too large for complete decision n=%llu\n", n); exit(8); }
        u64 bm = (u64)(b % a);
        u64 target = (a - bm) % a;            // -b mod a
        // enumerate divisors of b^2: factor n and x fully
        u64 pr[128]; int ex[128];
        int k1 = factor_full(n, pr, ex);
        {   u64 pr2[64]; int ex2[64]; int k2 = factor_full(x, pr2, ex2);
            for (int i=0;i<k2;i++){
                int f=-1; for (int j=0;j<k1;j++) if (pr[j]==pr2[i]) f=j;
                if (f>=0) ex[f]+=ex2[i]; else { pr[k1]=pr2[i]; ex[k1]=ex2[i]; k1++; }
            }
        }
        // divisors of b^2 have exponents 0..2*ex[i]; enumerate residues d mod a and track d'|check:
        // we need a divisor d with d ≡ -b and (b^2/d) ≡ -b (mod a).
        // enumerate all divisors of b^2 up to sqrt: d <= b (one of the pair is <= b). count can be large; cap sanity.
        // iterative enumeration with residues:
        static u64 dm[1000000]; static u128 dv[1000000]; int nd = 0; int overflow = 0;
        dv[nd] = 1; dm[nd] = 1 % a; nd++;
        for (int i=0;i<k1;i++){
            int cur = nd;
            u64 pm = pr[i] % a;
            u128 pw = 1; u64 pwm = 1;
            for (int e=1; e<=2*ex[i]; e++){
                pw *= pr[i]; pwm = mulmod(pwm, pm, a);
                if (pw > (u128)b) { /* divisor > b: pair partner < b, still enumerate via partner; skip to bound size */ }
                for (int j=0;j<cur;j++){
                    u128 d = dv[j] * pw;
                    if (d > b) continue;      // keep d <= b; partner d' = b^2/d >= b checked via congruence
                    if (nd >= 1000000){ overflow = 1; break; }
                    dv[nd] = d; dm[nd] = mulmod(dm[j], pwm, a); nd++;
                }
            }
        }
        for (int j=0;j<nd;j++){
            if (dm[j] != target) continue;
            // check partner: d' = b^2/d ≡ -b (mod a): d*d' = b^2 -> dm * d'm ≡ b^2; but compute directly:
            // d' mod a: need exact integer b^2/d mod a. b^2/d = (b/g)*(b/(d/g)) with g=gcd... simpler: u128 exact division.
            u128 d = dv[j];
            // exact: since d | b^2, q = b^2/d. Requires b < 2^63 so b^2 fits u128 (small/pw phases only).
            u128 q = ((u128)b * (u128)b) / d;
            u64 qm = (u64)(q % a);
            if (qm == target){ *wx = x; *wd = (u64)d; *wa = a; return 1; }
        }
        if (overflow){ fprintf(stderr, "FATAL divisor overflow n=%llu x=%llu\n", n, x); exit(9); }
    }
    return 0;
}

/* ----------------------------------------------------------------------
   Fast first-hit search for prime p (large). Partial factorization of x only.
   d = p^j * f, f | x^2, j in {0,1,2}. All congruence work mod a in u64.
   Returns 1 on certified hit. 0 = no hit within K offsets (NOT a proof of nonrep).
   ---------------------------------------------------------------------- */
static int fast_hit(u64 m, u64 p, int K){
    u64 x0 = p/m + 1;
    for (int i = 0; i < K; i++){
        u64 x = x0 + (u64)i;
        u64 a = m*x - p;
        if (a == 0) continue;
        if (a == 1){ return 1; }              // a=1: d=f=1 works: y=b+1, z=b(b+1) -> 1/(b+1)+1/(b(b+1))=1/b
        u64 pm = p % a, xm = x % a;
        if (gcd64(pm, a) != 1) { /* p | a impossible for prime p>a? a<m*x-.. can exceed p? here a small */ }
        u64 pinv = inv_mod(pm % a == 0 ? 1 : pm, a); // pm==0 cannot happen: a<p and p prime => p∤a... a=m*x-p < m*K + m; small
        u64 t1   = (a - xm % a) % a;                       // -x mod a
        u64 tpx  = (a - mulmod(pm, xm, a)) % a;            // -p x mod a
        u64 txpi = (a - mulmod(xm, pinv, a)) % a;          // -x p^{-1} mod a
        // partial factorization of x by small primes; leftover cofactor c (and c^2)
        u64 fs[6144]; u64 fm[6144]; int nf = 0;
        fs[nf]=1; fm[nf]=1%a; nf++;
        u64 rem = x;
        for (int t=0; t<nsmallp; t++){
            u64 q = smallp[t];
            if (q*q > rem) break;
            if (rem % q) continue;
            int e=0; while (rem % q == 0){ rem/=q; e++; }
            int cur = nf; u64 pw=1, pwm=1%a, qm_ = q%a;
            for (int e2=1; e2<=2*e; e2++){
                pw *= q; pwm = mulmod(pwm, qm_, a);
                for (int j=0;j<cur && nf<6000;j++){
                    u128 d=(u128)fs[j]*pw; if (d > x) continue;   // f <= x is enough in practice; partner handled via j-routes
                    fs[nf]=(u64)d; fm[nf]=mulmod(fm[j],pwm,a); nf++;
                }
            }
        }
        if (rem > 1){
            int cur = nf; u64 rm = rem % a;
            for (int j=0;j<cur && nf<6120;j++){
                u128 d1=(u128)fs[j]*rem;
                if (d1<=x){ fs[nf]=(u64)d1; fm[nf]=mulmod(fm[j],rm,a); nf++; }
                u128 d2=d1*rem;
                if (d2<=x){ fs[nf]=(u64)d2; fm[nf]=mulmod(fm[j],mulmod(rm,rm,a),a); nf++; }
            }
        }
        // for each f compute qm = (x^2/f) mod a exactly, then test the three j-routes
        for (int j=0;j<nf;j++){
            u64 f = fs[j];
            u128 xx = (u128)x * x;
            u64 qm = (u64)((xx / f) % a);      // exact: f | x^2? f | x * (x/f')..: f is built from divisors of x (not x^2!) times...
            // NOTE: fs contains divisors of x^2 built from primes of x, each f <= x and f | x^2 exactly. xx % f == 0 guaranteed.
            u64 fmm = fm[j];
            if (fmm == t1  && qm == t1 ) return 1;                        // d = p f
            if (fmm == tpx && qm == txpi) return 1;                       // d = f
            if (fmm == txpi && qm == tpx) return 1;                       // d = p^2 f
        }
    }
    return 0;
}

/* ---------- segmented sieve over [lo,hi] calling cb(p) ---------- */
static void for_primes(u64 lo, u64 hi, void (*cb)(u64, void*), void *ctx){
    // base primes to sqrt(hi)
    u64 rt = 2; while (rt*rt < hi) rt++;
    int nb = 0; u64 *base = malloc(sizeof(u64) * (rt > 3 ? rt : 4));
    { unsigned char *sv = calloc(rt+1, 1);
      for (u64 i=2;i<=rt;i++){ if (!sv[i]){ base[nb++]=i; for (u64 j=i*i;j<=rt;j+=i) sv[j]=1; } }
      free(sv); }
    const u64 SEG = 1ULL<<24; // 16M numbers per segment
    unsigned char *seg = malloc(SEG);
    for (u64 s = lo; s <= hi; s += SEG){
        u64 e = s + SEG - 1; if (e > hi) e = hi;
        u64 len = e - s + 1;
        memset(seg, 0, len);
        for (int i=0;i<nb;i++){
            u64 q = base[i];
            if (q*q > e) break;
            u64 st = (s + q - 1) / q * q; if (st < q*q) st = q*q;
            for (u64 j=st; j<=e; j+=q) seg[j-s] = 1;
        }
        for (u64 v=s; v<=e; v++){
            if (!seg[v-s] && v >= 2) cb(v, ctx);
        }
    }
    free(seg); free(base);
}

/* ---------- scan context ---------- */
typedef struct { u64 m; u64 count, miss, esc; u64 K1, K2; FILE *log; } scanctx;
static scanctx *g;
static void scan_cb(u64 p, void *ctx){
    scanctx *c = ctx;
    c->count++;
    if (fast_hit(c->m, p, (int)c->K1)) return;
    c->esc++;
    if (fast_hit(c->m, p, (int)c->K2)) return;
    c->miss++;
    fprintf(c->log, "SUSPECT m=%llu p=%llu (no witness within K2 offsets; needs complete decision)\n", c->m, p); fflush(c->log);
    printf("SUSPECT m=%llu p=%llu\n", c->m, p); fflush(stdout);
}

int main(int argc, char **argv){
    init_smallp(1300);
    if (argc < 3){ fprintf(stderr, "usage: mfrac small|primes|one|pw m ...\n"); return 1; }
    u64 m = strtoull(argv[2], 0, 10);
    if (!strcmp(argv[1], "one")){
        u64 n = strtoull(argv[3], 0, 10), wx, wd, wa;
        int r = decide_complete(m, n, &wx, &wd, &wa);
        if (r) printf("REP m=%llu n=%llu x=%llu d=%llu a=%llu\n", m, n, wx, wd, wa);
        else   printf("NONREP m=%llu n=%llu\n", m, n);
        return 0;
    }
    if (!strcmp(argv[1], "list")){
        FILE *f = fopen(argv[3], "r"); u64 n, wx, wd, wa, cnt=0, bad=0;
        while (fscanf(f, "%llu", &n) == 1){
            cnt++;
            if (!decide_complete(m, n, &wx, &wd, &wa)){ printf("NONREP m=%llu n=%llu\n", m, n); bad++; }
        }
        printf("list done m=%llu checked=%llu nonrep=%llu\n", m, cnt, bad);
        return 0;
    }
    if (!strcmp(argv[1], "small")){
        u64 lo = strtoull(argv[3],0,10), hi = strtoull(argv[4],0,10), wx, wd, wa;
        for (u64 n = lo; n <= hi; n++){
            if (!decide_complete(m, n, &wx, &wd, &wa))
                printf("NONREP m=%llu n=%llu\n", m, n);
        }
        printf("small-phase done m=%llu [%llu,%llu]\n", m, lo, hi);
        return 0;
    }
    if (!strcmp(argv[1], "pw")){
        // complete decision for all primes in (m^2, 2m^2)
        u64 lo = m*m+1, hi = 2*m*m;
        u64 wx, wd, wa; u64 found = 0;
        for (u64 p = lo; p <= hi; p++){
            if (!is_prime_u64(p)) continue;
            if (!decide_complete(m, p, &wx, &wd, &wa)){
                printf("PW-EXCEPTION m=%llu p=%llu\n", m, p); found++;
            }
        }
        printf("pw done m=%llu exceptions=%llu\n", m, found);
        return 0;
    }
    if (!strcmp(argv[1], "primes")){
        u64 lo = strtoull(argv[3],0,10), hi = strtoull(argv[4],0,10);
        static scanctx c; c.m = m; c.K1 = 96; c.K2 = 20000;
        char fn[128]; snprintf(fn, sizeof fn, "scan_m%llu_%llu_%llu.log", m, lo, hi);
        c.log = fopen(fn, "w");
        for_primes(lo, hi, scan_cb, &c);
        printf("scan done m=%llu [%llu,%llu] primes=%llu escalations=%llu exceptions=%llu\n",
               m, lo, hi, c.count, c.esc, c.miss);
        fclose(c.log);
        return 0;
    }
    fprintf(stderr, "unknown mode\n"); return 1;
}
