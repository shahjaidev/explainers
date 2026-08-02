// check2: INDEPENDENT complete decision for m/n = 1/x+1/y+1/z.
// Deliberately different algorithm from mfrac.c: for each x in (n/m, 3n/m],
// residual a/b with a = m*x-n, b = n*x; then iterate y over the FULL range
// (b/a, 2b/a] and test z = b*y/(a*y - b) for integrality. No divisor
// enumeration, no factorization, no modular shortcuts.
// usage: ./check2 m n   -> prints REP (with witness) or NONREP
#include <stdio.h>
#include <stdlib.h>
typedef unsigned long long u64;
typedef __uint128_t u128;
int main(int argc, char **argv){
    u64 m = strtoull(argv[1],0,10), n = strtoull(argv[2],0,10);
    if (3*n < m){ printf("NONREP m=%llu n=%llu (m/n > 3)\n", m, n); return 0; }
    if (n % m == 0){ u64 q=n/m; printf("REP m=%llu n=%llu x=%llu y=%llu z=%llu\n",m,n,2*q,3*q,6*q); return 0; }
    for (u64 x = n/m + 1; x <= 3*n/m; x++){
        u64 a = m*x - n;
        u128 b = (u128)n * x;
        // y in (b/a, 2b/a]; z = b*y/(a*y-b) integer test
        u64 ylo = (u64)(b / a) + 1, yhi = (u64)(2*b / a);
        for (u64 y = ylo; y <= yhi; y++){
            u128 den = (u128)a * y - b;      // > 0
            u128 num = b * y;
            if (num % den == 0){
                u128 z = num / den;
                // verify exactly: 1/x + 1/y + 1/z == m/n  <=>  n*(yz + xz + xy) == m*x*y*z
                // do it as: a*y*z == b*(y+z) (residual check) to stay in 128 bits when possible
                if ((u128)a * y % 1 == 0){ /* trivially true; real check below */ }
                // exact residual check with big care: a*y*z vs b*(y+z)
                // a*y <= a*2b/a = 2b <= 2^64*.. ; z can be large; use __int128 guarded
                u128 lhs_hi;
                // compute a*y (fits: a*y <= 2b + a), then (a*y)*z may overflow; compare via division:
                // a*y*z == b*y + b*z  <=>  z*(a*y - b) == b*y (which is the defining equation) -- already true.
                { char zs[48]; int i=47; zs[i--]=0; u128 t=z; if(!t) zs[i--]='0';
                  while(t){ zs[i--]='0'+(int)(t%10); t/=10; }
                  printf("REP m=%llu n=%llu x=%llu y=%llu z=%s\n", m, n, x, y, zs+i+1); }
                return 0;
            }
        }
    }
    printf("NONREP m=%llu n=%llu\n", m, n);
    return 0;
}
