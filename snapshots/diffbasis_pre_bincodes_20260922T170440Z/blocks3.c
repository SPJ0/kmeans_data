/* Block model with EXHAUSTIVE coordinate descent on block offsets.
   Outer loop: random/SA over gaps & sizes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAXB 8
static int K,N,MAXVAL,M;
static int nb[MAXB],gb[MAXB],ob[MAXB];
static unsigned char *base;   /* coverage by pairs not involving block i */
static int *stamp, curstamp;
static unsigned long long rs=1;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int m){ return (int)(rnd()%(unsigned)m); }

static int marks[600], nm;
static int others[600], no;

static void buildMarks(void){
  nm=0;
  for(int i=0;i<M;i++) for(int j=0;j<nb[i];j++) marks[nm++]=ob[i]+j*gb[i];
}
static int missingAll(void){
  buildMarks();
  static unsigned char *cov=0; if(!cov) cov=malloc(N+2);
  memset(cov,0,N+1);
  for(int i=0;i<nm;i++) for(int j=i+1;j<nm;j++){ int d=marks[i]-marks[j]; if(d<0)d=-d; if(d>=1&&d<=N) cov[d]=1; }
  int miss=0; for(int d=1;d<=N;d++) if(!cov[d]) miss++;
  return miss;
}
/* optimize offset of block bi exhaustively given others */
static int optBlock(int bi){
  /* base coverage from marks not in block bi */
  no=0;
  for(int i=0;i<M;i++){ if(i==bi) continue; for(int j=0;j<nb[i];j++) others[no++]=ob[i]+j*gb[i]; }
  memset(base,0,N+1);
  for(int i=0;i<no;i++) for(int j=i+1;j<no;j++){ int d=others[i]-others[j]; if(d<0)d=-d; if(d>=1&&d<=N) base[d]=1; }
  /* internal differences of block bi (offset independent) */
  for(int a=1;a<nb[bi];a++){ int d=a*gb[bi]; if(d>=1&&d<=N) base[d]=1; }
  int bmiss=0; for(int d=1;d<=N;d++) if(!base[d]) bmiss++;
  int bestGain=-1,bestO=ob[bi],n=nb[bi],g=gb[bi];
  int maxo = MAXVAL-(n-1)*g; if(maxo<0) return 1<<28;
  for(int o=0;o<=maxo;o++){
    curstamp++;
    int gain=0;
    for(int a=0;a<n;a++){
      int v=o+a*g;
      for(int t=0;t<no;t++){
        int d=v-others[t]; if(d<0)d=-d;
        if(d>=1&&d<=N&&!base[d]&&stamp[d]!=curstamp){ stamp[d]=curstamp; gain++; }
      }
    }
    if(gain>bestGain){ bestGain=gain; bestO=o; }
  }
  ob[bi]=bestO;
  return bmiss-bestGain;
}
int main(int argc,char**argv){
  K=atoi(argv[1]); N=atoi(argv[2]); MAXVAL=atoi(argv[3]); double secs=atof(argv[4]);
  rs=strtoull(argv[5],0,10)*2862933555777941757ULL+3037000493ULL;
  M=atoi(argv[6]);
  const char*outf=(argc>7)?argv[7]:"b3.txt";
  base=malloc(N+2); stamp=calloc(N+2,sizeof(int));
  int gmin=atoi(argv[8]), gmax=atoi(argv[9]);
  int globalBest=1<<28; int bo[MAXB],bg[MAXB],bn[MAXB];
  clock_t t0=clock();
  while((double)(clock()-t0)/CLOCKS_PER_SEC<secs){
    /* random sizes (near equal, perturbed) and gaps */
    int rem=K;
    for(int i=0;i<M;i++){ int base_n=rem/(M-i); int d=rndi(7)-3; if(i==M-1) nb[i]=rem; else { nb[i]=base_n+d; if(nb[i]<2)nb[i]=2; if(nb[i]>rem-2*(M-i-1)) nb[i]=rem-2*(M-i-1); } rem-=nb[i]; }
    for(int i=0;i<M;i++){ gb[i]=gmin+rndi(gmax-gmin+1); ob[i]=rndi(MAXVAL/2); }
    ob[0]=0;
    int prev=1<<28;
    for(int sweep=0;sweep<8;sweep++){
      int cur=0;
      for(int i=0;i<M;i++) cur=optBlock(i);
      if(cur>=prev) { prev=cur; break; }
      prev=cur;
    }
    int miss=missingAll();
    if(miss<globalBest){
      globalBest=miss; memcpy(bo,ob,sizeof ob);memcpy(bg,gb,sizeof gb);memcpy(bn,nb,sizeof nb);
      fprintf(stderr,"miss=%d  ",miss);
      for(int i=0;i<M;i++) fprintf(stderr,"(%d,%d,%d) ",bo[i],bg[i],bn[i]);
      fprintf(stderr,"\n"); fflush(stderr);
      FILE*f=fopen(outf,"w"); memcpy(ob,bo,sizeof bo);memcpy(gb,bg,sizeof bg);memcpy(nb,bn,sizeof bn);
      buildMarks(); for(int i=0;i<nm;i++) fprintf(f,"%d ",marks[i]); fprintf(f,"\n"); fclose(f);
    }
  }
  printf("%d\n",globalBest);
  return 0;
}
