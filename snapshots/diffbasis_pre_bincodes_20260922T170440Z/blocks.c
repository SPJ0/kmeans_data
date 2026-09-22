/* Search over "run-length" structures: B is defined by consecutive gaps,
   grouped into runs (g_i repeated c_i times).  Maximize coverage of 1..N. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define SMAX 20
static int K,N;
static int S;                  /* number of runs */
static int gp[SMAX], ct[SMAX];
static int el[600];
static unsigned char *cov;

static unsigned long long rs=88172645463325252ULL;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int m){ return (int)(rnd()%(unsigned)m); }
static inline double rndd(void){ return (double)(rnd()>>11)/9007199254740992.0; }

static int build(int*g,int*c,int s){
  int n=0; el[n++]=0;
  for(int i=0;i<s;i++) for(int j=0;j<c[i];j++){ if(n>=K) return n; el[n]=el[n-1]+g[i]; n++; }
  return n;
}
static int evalset(int n){
  memset(cov,0,N+1);
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++){ int d=el[j]-el[i]; if(d<=N) cov[d]=1; }
  int miss=0; for(int d=1;d<=N;d++) if(!cov[d]) miss++;
  return miss;
}
static int score(int*g,int*c,int s){
  int tot=0; for(int i=0;i<s;i++){ if(g[i]<1) return 1<<28; tot+=c[i]; }
  if(tot!=K-1) return 1<<28;
  int n=build(g,c,s); if(n!=K) return 1<<28;
  return evalset(n);
}
int main(int argc,char**argv){
  K=atoi(argv[1]); N=atoi(argv[2]); double secs=atof(argv[3]);
  rs=strtoull(argv[4],0,10)*2862933555777941757ULL+3037000493ULL;
  S=atoi(argv[5]);
  cov=malloc(N+2);
  /* init: random runs */
  if(argc>6){ /* seed file: pairs gap count */
    FILE*f=fopen(argv[6],"r"); S=0; while(fscanf(f,"%d %d",&gp[S],&ct[S])==2) S++; fclose(f);
  } else {
    int rem=K-1;
    for(int i=0;i<S;i++){ ct[i]= (i==S-1)? rem : 1+rndi(rem/(S-i)+1); rem-=ct[i]; gp[i]=1+rndi(60); }
  }
  int cur=score(gp,ct,S);
  int best=cur; int bg[SMAX],bc[SMAX],bs=S; memcpy(bg,gp,sizeof gp); memcpy(bc,ct,sizeof ct);
  clock_t t0=clock(); double T=40.0; long long it=0;
  int ng[SMAX],nc[SMAX];
  while(1){
    if((it&0x3FF)==0){ double e=(double)(clock()-t0)/CLOCKS_PER_SEC; if(e>secs)break;
      double frac=fmod(e/secs*6.0,1.0); T=60.0*pow(0.3/60.0,frac); }
    it++;
    memcpy(ng,gp,sizeof gp); memcpy(nc,ct,sizeof ct); int ns=S;
    int mv=rndi(100);
    if(mv<40){ int i=rndi(ns); int dlt=1+rndi(3); ng[i]+= (rnd()&1)?dlt:-dlt; if(ng[i]<1) continue; }
    else if(mv<55){ int i=rndi(ns); ng[i]=1+rndi(3*N/K+20); }
    else if(mv<85){ int i=rndi(ns),j=rndi(ns); if(i==j)continue; int amt=1+rndi(2); if(nc[i]<=amt)continue; nc[i]-=amt; nc[j]+=amt; }
    else { int i=rndi(ns),j=rndi(ns); if(i==j)continue; int t=ng[i];ng[i]=ng[j];ng[j]=t; t=nc[i];nc[i]=nc[j];nc[j]=t; }
    int sc=score(ng,nc,ns); if(sc>=(1<<28)) continue;
    int dE=sc-cur;
    if(dE<=0 || rndd()<exp(-dE/T)){
      memcpy(gp,ng,sizeof gp); memcpy(ct,nc,sizeof ct); S=ns; cur=sc;
      if(cur<best){ best=cur; memcpy(bg,gp,sizeof gp); memcpy(bc,ct,sizeof ct); bs=S; }
    }
  }
  fprintf(stderr,"best_missing=%d evals=%lld\n",best,it);
  printf("%d\n",best);
  for(int i=0;i<bs;i++) printf("%d*%d ",bg[i],bc[i]); printf("\n");
  int n=build(bg,bc,bs);
  for(int i=0;i<n;i++) printf("%d ",el[i]); printf("\n");
  return 0;
}
