// Element-level SA: start from a set file (one int per line), move single elements to cover [1,TARGET].
// Usage: free_sa infile seed iters T0 outfile
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define TARGET 6166
#define MAXV 16384
int n, A[256];
int cnt[2*MAXV+2];
static unsigned long long rs;
static inline unsigned rnd(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return (unsigned)(rs>>11); }
int covered;
static inline void add(int d,int s){ if(d<0)d=-d; if(d==0||d>TARGET) return; if(s>0){ if(cnt[d]++==0) covered++; } else { if(--cnt[d]==0) covered--; } }
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); n=0; while(fscanf(f,"%d",&A[n])==1) n++; fclose(f);
  rs=88172645463325252ULL ^ (unsigned long long)atoll(argv[2])*2654435761ULL; for(int i=0;i<10;i++) rnd();
  long iters=atol(argv[3]); double T0=atof(argv[4]);
  int lo=A[0],hi=A[0]; for(int i=0;i<n;i++){ if(A[i]<lo)lo=A[i]; if(A[i]>hi)hi=A[i]; }
  for(int i=0;i<n;i++) A[i]-=lo; hi-=lo;
  int span = hi+200; if(span>MAXV-1) span=MAXV-1;
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++) add(A[i]-A[j],1);
  int best=covered; printf("start covered %d\n",covered);
  int miss[TARGET+1];
  for(long it=0;it<iters;it++){
    double T=T0*(1.0-(double)it/iters)+1e-3;
    int i=rnd()%n, x=A[i], nx;
    if(rnd()%2){ // targeted: pick missing d
      int nm=0; for(int d=1;d<=TARGET&&nm<64;d++){ int dd=1+rnd()%TARGET; if(!cnt[dd]) {miss[nm++]=dd;} if(nm) break; }
      if(!nm){ nx=rnd()%span; }
      else { int d=miss[0]; int y=A[rnd()%n]; nx = (rnd()&1)? y+d : y-d; }
    } else nx = x + (int)(rnd()%41)-20;
    if(nx<0||nx>=span) continue;
    int dup=0; for(int j=0;j<n;j++) if(A[j]==nx){dup=1;break;} if(dup) continue;
    int before=covered;
    for(int j=0;j<n;j++) if(j!=i) add(x-A[j],-1);
    for(int j=0;j<n;j++) if(j!=i) add(nx-A[j],1);
    int delta=covered-before;
    if(delta>=0 || exp(delta/T) > (rnd()%1000000)/1e6){ A[i]=nx;
      if(covered>best){ best=covered; if(best>=TARGET-5) {printf("it %ld best %d\n",it,best); fflush(stdout);} }
      if(covered==TARGET){ FILE*g=fopen(argv[5],"w"); for(int k=0;k<n;k++) fprintf(g,"%d\n",A[k]); fclose(g); printf("FOUND\n"); return 0; }
    } else {
      for(int j=0;j<n;j++) if(j!=i) add(nx-A[j],-1);
      for(int j=0;j<n;j++) if(j!=i) add(x-A[j],1);
    }
  }
  printf("final best %d covered %d\n",best,covered);
  return 1;
}
