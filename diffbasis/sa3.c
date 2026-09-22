/* SA over explicit mark sets with structured (block/suffix/stretch) moves. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static int K,N,MAXVAL,W;
static int m0[600],m1[600];
static unsigned long long *cov;
static int *ulist,nu;
static unsigned long long rs=1;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int x){ return (int)(rnd()%(unsigned)x); }
static inline double rndd(void){ return (double)(rnd()>>11)/9007199254740992.0; }
static int cmpi(const void*a,const void*b){return *(const int*)a-*(const int*)b;}

static int evaluate(int*m){          /* returns #missing in 1..N ; m must be sorted */
  memset(cov,0,W*8);
  for(int i=0;i<K;i++){ int mi=m[i];
    for(int j=i+1;j<K;j++){ int d=m[j]-mi; if(d>N) break; cov[d>>6]|=1ULL<<(d&63); }
  }
  int c=0; for(int w=0;w<W;w++) c+=__builtin_popcountll(cov[w]);
  if(cov[0]&1ULL) c--;                       /* d=0 never set anyway */
  /* bits above N */
  for(int d=N+1;d<W*64;d++) if(cov[d>>6]>>(d&63)&1ULL) c--;
  return N-c;
}
static void collectMissing(int*m){
  nu=0; for(int d=1;d<=N;d++) if(!((cov[d>>6]>>(d&63))&1ULL)) ulist[nu++]=d;
}
static int okset(int*m){
  for(int i=0;i<K;i++){ if(m[i]<0||m[i]>MAXVAL) return 0; }
  for(int i=1;i<K;i++) if(m[i]==m[i-1]) return 0;
  return 1;
}
int main(int argc,char**argv){
  K=atoi(argv[1]); N=atoi(argv[2]); MAXVAL=atoi(argv[3]); double secs=atof(argv[4]);
  rs=strtoull(argv[5],0,10)*2862933555777941757ULL+3037000493ULL;
  const char*seedf=(argv[6][0]=='-')?0:argv[6];
  const char*outf=argv[7];
  double T0=(argc>8)?atof(argv[8]):8.0, T1=(argc>9)?atof(argv[9]):0.25;
  W=(MAXVAL+64)/64+2; cov=malloc(W*8); ulist=malloc(sizeof(int)*(N+2));
  if(seedf){ FILE*f=fopen(seedf,"r"); int v,i=0; while(fscanf(f,"%d",&v)==1&&i<K) m0[i++]=v; fclose(f);
             while(i<K){ int v2=rndi(MAXVAL+1); m0[i++]=v2; } }
  else { m0[0]=0; for(int i=1;i<K;i++) m0[i]=rndi(MAXVAL+1); }
  qsort(m0,K,sizeof(int),cmpi);
  for(int i=1;i<K;i++) if(m0[i]<=m0[i-1]) m0[i]=m0[i-1]+1;
  int cur=evaluate(m0); collectMissing(m0);
  int best=cur; int bm[600]; memcpy(bm,m0,sizeof(int)*K);
  clock_t t0=clock(); long long it=0; double T=T0;
  int sinceCollect=0;
  while(1){
    if((it&0xFF)==0){ double e=(double)(clock()-t0)/CLOCKS_PER_SEC; if(e>secs) break;
      double frac=fmod(e/secs*6.0,1.0); T=T0*pow(T1/T0,frac); }
    it++;
    memcpy(m1,m0,sizeof(int)*K);
    int mv=rndi(100);
    if(mv<35){                                  /* single mark -> guided */
      int i=1+rndi(K-1);
      int v;
      if(nu>0&&(rnd()&3)){ int d=ulist[rndi(nu)]; int j=rndi(K); v=(rnd()&1)?m0[j]+d:m0[j]-d; }
      else { v=m0[i]+(rndi(21)-10); }
      if(v<0||v>MAXVAL) continue; m1[i]=v;
    } else if(mv<60){                           /* suffix shift */
      int i=1+rndi(K-1); int d=1+rndi(5); if(rnd()&1) d=-d;
      for(int t=i;t<K;t++) m1[t]+=d;
    } else if(mv<80){                           /* block shift */
      int i=1+rndi(K-1); int len=1+rndi(30); int j=i+len; if(j>K) j=K;
      int d=1+rndi(4); if(rnd()&1) d=-d;
      for(int t=i;t<j;t++) m1[t]+=d;
    } else if(mv<92){                           /* stretch (gap change of a run) */
      int i=1+rndi(K-1); int len=2+rndi(30); int j=i+len; if(j>K) j=K;
      int d=(rnd()&1)?1:-1;
      for(int t=i;t<j;t++) m1[t]+=(t-i+1)*d;
      for(int t=j;t<K;t++) m1[t]+=(j-i)*d;
    } else {                                    /* swap two gaps */
      int i=1+rndi(K-1), j=1+rndi(K-1); if(i==j) continue; if(i>j){int t=i;i=j;j=t;}
      int gi=m0[i]-m0[i-1], gj=m0[j]-m0[j-1]; int diff=gj-gi;
      for(int t=i;t<j;t++) m1[t]+=diff;
    }
    qsort(m1,K,sizeof(int),cmpi);
    if(!okset(m1)) continue;
    int sc=evaluate(m1);
    int dE=sc-cur;
    if(dE<=0||rndd()<exp(-dE/T)){
      memcpy(m0,m1,sizeof(int)*K); cur=sc;
      if(++sinceCollect>200){ evaluate(m0); collectMissing(m0); sinceCollect=0; }
      if(cur<best){ best=cur; memcpy(bm,m0,sizeof(int)*K);
        if(best==0) break; }
    }
  }
  fprintf(stderr,"best_missing=%d iters=%lld\n",best,it);
  FILE*f=fopen(outf,"w"); for(int i=0;i<K;i++) fprintf(f,"%d ",bm[i]); fclose(f);
  printf("%d\n",best);
  return 0;
}
