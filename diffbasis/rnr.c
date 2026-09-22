/* Ruin-and-recreate local search for difference bases. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static int K,N,MAXVAL,nk;
static int el[600];
static int *cnt;          /* coverage count per d */
static char *used;
static int *ulist,*upos,nu;   /* uncovered set */
static int *gain,*lastd;
static unsigned long long rs=88172645463325252ULL;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int m){ return (int)(rnd()%(unsigned)m); }

static inline void uAdd(int d){ upos[d]=nu; ulist[nu++]=d; }
static inline void uDel(int d){ int p=upos[d],last=ulist[--nu]; ulist[p]=last; upos[last]=p; }
static void addMark(int v){
  for(int j=0;j<nk;j++){ int d=v-el[j]; if(d<0)d=-d; if(d<=N){ if(cnt[d]++==0) uDel(d);} }
  el[nk++]=v; used[v]=1;
}
static void delMarkIdx(int i){
  int v=el[i]; el[i]=el[--nk];
  for(int j=0;j<nk;j++){ int d=v-el[j]; if(d<0)d=-d; if(d<=N){ if(--cnt[d]==0) uAdd(d);} }
  used[v]=0;
}
static void reset(void){
  memset(cnt,0,sizeof(int)*(N+2)); nu=0; for(int d=1;d<=N;d++) uAdd(d);
  memset(used,0,MAXVAL+2);
}
/* greedy: insert the mark maximizing newly covered uncovered-differences */
static void greedyInsert(int noise){
  memset(gain,0,sizeof(int)*(MAXVAL+2));
  memset(lastd,-1,sizeof(int)*(MAXVAL+2));
  for(int t=0;t<nu;t++){
    int d=ulist[t];
    for(int j=0;j<nk;j++){
      int v=el[j]+d; if(v<=MAXVAL && !used[v] && lastd[v]!=d){ lastd[v]=d; gain[v]++; }
      v=el[j]-d; if(v>=0 && !used[v] && lastd[v]!=d){ lastd[v]=d; gain[v]++; }
    }
  }
  int bg=-1,bv=-1,ties=0;
  for(int v=0;v<=MAXVAL;v++){
    if(used[v]) continue;
    int g=gain[v]; if(noise) g=g*16+rndi(16);
    if(g>bg){ bg=g; bv=v; ties=1; }
    else if(g==bg){ ties++; if(rndi(ties)==0) bv=v; }
  }
  if(bv<0) bv=rndi(MAXVAL+1);
  addMark(bv);
}
int main(int argc,char**argv){
  K=atoi(argv[1]); N=atoi(argv[2]); MAXVAL=atoi(argv[3]); double secs=atof(argv[4]);
  rs=strtoull(argv[5],0,10)*2862933555777941757ULL+3037000493ULL;
  const char*seedf=(argc>6&&argv[6][0]!='-')?argv[6]:0;
  const char*outf=(argc>7)?argv[7]:"best.txt";
  cnt=malloc(sizeof(int)*(N+2)); used=malloc(MAXVAL+2);
  ulist=malloc(sizeof(int)*(N+2)); upos=malloc(sizeof(int)*(N+2));
  gain=malloc(sizeof(int)*(MAXVAL+2)); lastd=malloc(sizeof(int)*(MAXVAL+2));
  reset(); nk=0;
  if(seedf){ FILE*f=fopen(seedf,"r"); int v; while(fscanf(f,"%d",&v)==1&&nk<K){ if(v>=0&&v<=MAXVAL&&!used[v]) addMark(v);} fclose(f); }
  if(nk==0) addMark(0);
  while(nk<K) greedyInsert(1);
  int best=nu, bestEl[600]; memcpy(bestEl,el,sizeof(int)*nk);
  int cur=nu;
  clock_t t0=clock(); long long it=0;
  while((double)(clock()-t0)/CLOCKS_PER_SEC < secs){
    it++;
    int r=1+rndi(6);
    int saved[16],ns=0;
    for(int t=0;t<r;t++){ int i=rndi(nk); saved[ns++]=el[i]; delMarkIdx(i); }
    while(nk<K) greedyInsert(1);
    if(nu<=cur){ cur=nu; if(nu<best){ best=nu; memcpy(bestEl,el,sizeof(int)*nk);
        if(best==0) break; } }
    else {
      /* restore previous best occasionally */
      if(rndi(100)<70){ nk=0; reset(); for(int i=0;i<K;i++) addMark(bestEl[i]); cur=nu; }
      else cur=nu;
    }
  }
  fprintf(stderr,"best_missing=%d iters=%lld\n",best,it);
  FILE*f=fopen(outf,"w"); for(int i=0;i<K;i++) fprintf(f,"%d ",bestEl[i]); fprintf(f,"\n"); fclose(f);
  printf("%d\n",best);
  return 0;
}
