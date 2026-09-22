/* Difference basis search: find K nonneg integers whose pairwise differences cover 1..N */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static int K, N, MAXVAL;
static int el[512];
static int *cnt;      /* cnt[d] for d in 0..N */
static char *used;    /* used[v] for v in 0..MAXVAL */
static int *missList, *missPos, missing;

static unsigned long long rs = 88172645463325252ULL;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int m){ return (int)(rnd()%(unsigned)m); }
static inline double rndd(void){ return (double)(rnd()>>11)/9007199254740992.0; }

static inline void missAdd(int d){ missPos[d]=missing; missList[missing++]=d; }
static inline void missDel(int d){ int p=missPos[d]; int last=missList[--missing]; missList[p]=last; missPos[last]=p; }

static inline void decD(int d){ if(d>=1&&d<=N){ if(--cnt[d]==0) missAdd(d);} }
static inline void incD(int d){ if(d>=1&&d<=N){ if(cnt[d]++==0) missDel(d);} }

static void removeElem(int i){
  int v=el[i];
  for(int j=0;j<K;j++){ if(j==i) continue; int d=v-el[j]; if(d<0)d=-d; decD(d); }
  used[v]=0;
}
static void addElem(int i,int v){
  for(int j=0;j<K;j++){ if(j==i) continue; int d=v-el[j]; if(d<0)d=-d; incD(d); }
  el[i]=v; used[v]=1;
}
static void rebuild(void){
  memset(cnt,0,sizeof(int)*(N+1));
  missing=0; for(int d=1;d<=N;d++) missAdd(d);
  memset(used,0,MAXVAL+1);
  for(int i=0;i<K;i++) used[el[i]]=1;
  for(int i=0;i<K;i++) for(int j=i+1;j<K;j++){ int d=el[i]-el[j]; if(d<0)d=-d; incD(d);}    
}

int main(int argc,char**argv){
  /* args: K N MAXVAL seconds seed [infile] */
  K=atoi(argv[1]); N=atoi(argv[2]); MAXVAL=atoi(argv[3]);
  double secs=atof(argv[4]); rs=strtoull(argv[5],0,10)*2862933555777941757ULL+3037000493ULL;
  cnt=malloc(sizeof(int)*(N+2)); used=malloc(MAXVAL+2);
  missList=malloc(sizeof(int)*(N+2)); missPos=malloc(sizeof(int)*(N+2));
  if(argc>6){
    FILE*f=fopen(argv[6],"r"); int v,i=0; while(fscanf(f,"%d",&v)==1&&i<K) el[i++]=v; fclose(f);
    if(i<K){ /* pad with random unused */
      char*u=calloc(MAXVAL+2,1); for(int t=0;t<i;t++)u[el[t]]=1;
      while(i<K){ int v2=rndi(MAXVAL+1); if(!u[v2]){u[v2]=1; el[i++]=v2;} }
      free(u);
    }
  } else {
    char*u=calloc(MAXVAL+2,1); el[0]=0; u[0]=1;
    for(int i=1;i<K;i++){ int v; do{v=rndi(MAXVAL+1);}while(u[v]); u[v]=1; el[i]=v; }
    free(u);
  }
  rebuild();
  int best=missing; int bestEl[512]; memcpy(bestEl,el,sizeof(int)*K);
  clock_t t0=clock();
  double T=3.0;
  long long it=0;
  while(1){
    if((it&0xFFFFF)==0){
      double el_t=(double)(clock()-t0)/CLOCKS_PER_SEC;
      if(el_t>secs) break;
      /* cyclic reheat */
      double frac=fmod(el_t/secs*8.0,1.0);
      T=3.0*pow(0.02/3.0,frac);
    }
    it++;
    int i=rndi(K); if(el[i]==0&&i==0) i=rndi(K);
    int v;
    if(missing>0 && (rnd()&3)){
      int d=missList[rndi(missing)];
      int j=rndi(K);
      v = (rnd()&1)? el[j]+d : el[j]-d;
      if(v<0||v>MAXVAL) continue;
    } else {
      v=rndi(MAXVAL+1);
    }
    if(used[v]) continue;
    int old=el[i], om=missing;
    removeElem(i); addElem(i,v);
    int dE=missing-om;
    if(dE<=0 || rndd()<exp(-dE/T)){
      if(missing<best){ best=missing; memcpy(bestEl,el,sizeof(int)*K); if(best==0) break; }
    } else { removeElem(i); addElem(i,old); }
  }
  fprintf(stderr,"best_missing=%d iters=%lld\n",best,it);
  /* print best */
  int tmp[512]; memcpy(tmp,bestEl,sizeof(int)*K);
  for(int a=0;a<K;a++)for(int b=a+1;b<K;b++) if(tmp[b]<tmp[a]){int t=tmp[a];tmp[a]=tmp[b];tmp[b]=t;}
  printf("%d\n",best);
  for(int i=0;i<K;i++) printf("%d ",tmp[i]);
  printf("\n");
  return 0;
}
