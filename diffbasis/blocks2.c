/* Search over unions of arithmetic progressions (offset,gap,count), blocks may interleave. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define MAXB 12
static int K,N,MAXVAL,S;
static int ob[MAXB],gb[MAXB],nb[MAXB];
static int el[1024], nel;
static unsigned char *cov;
static unsigned long long rs=88172645463325252ULL;
static inline unsigned long long rnd(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static inline int rndi(int m){ return (int)(rnd()%(unsigned)m); }
static inline double rndd(void){ return (double)(rnd()>>11)/9007199254740992.0; }
static int cmpi(const void*a,const void*b){ return *(const int*)a-*(const int*)b; }

static int build(int*o,int*g,int*n,int s){
  int m=0;
  for(int i=0;i<s;i++){
    if(g[i]<1||n[i]<1) return -1;
    long long hi=(long long)o[i]+(long long)(n[i]-1)*g[i];
    if(o[i]<0||hi>MAXVAL) return -1;
    for(int j=0;j<n[i];j++){ if(m>=1024) return -1; el[m++]=o[i]+j*g[i]; }
  }
  qsort(el,m,sizeof(int),cmpi);
  int u=0; for(int i=0;i<m;i++) if(i==0||el[i]!=el[i-1]) el[u++]=el[i];
  nel=u; if(u>K) return -1;
  return u;
}
static int score(int*o,int*g,int*n,int s){
  int m=build(o,g,n,s); if(m<0) return 1<<28;
  memset(cov,0,N+1);
  for(int i=0;i<m;i++) for(int j=i+1;j<m;j++){ int d=el[j]-el[i]; if(d<=N) cov[d]=1; else break; }
  int miss=0; for(int d=1;d<=N;d++) if(!cov[d]) miss++;
  return miss;
}
int main(int argc,char**argv){
  K=atoi(argv[1]); N=atoi(argv[2]); MAXVAL=atoi(argv[3]); double secs=atof(argv[4]);
  rs=strtoull(argv[5],0,10)*2862933555777941757ULL+3037000493ULL; S=atoi(argv[6]);
  cov=malloc(N+2);
  const char*seed = (argc>7)?argv[7]:0;
  if(seed){ FILE*f=fopen(seed,"r"); S=0; while(fscanf(f,"%d %d %d",&ob[S],&gb[S],&nb[S])==3) S++; fclose(f); }
  else {
    int rem=K;
    for(int i=0;i<S;i++){ nb[i]=(i==S-1)?rem:(rem/(S-i)); rem-=nb[i]; gb[i]=1+rndi(2*N/K+2); ob[i]=rndi(N); }
  }
  int cur=score(ob,gb,nb,S), tries=0;
  while(cur>=(1<<28) && tries++<10000){
    int rem=K; for(int i=0;i<S;i++){ nb[i]=(i==S-1)?rem:(rem/(S-i)); rem-=nb[i]; gb[i]=1+rndi(2*N/K+2); ob[i]=rndi(N/2); }
    cur=score(ob,gb,nb,S);
  }
  int best=cur,bo[MAXB],bg[MAXB],bn[MAXB];
  memcpy(bo,ob,sizeof ob);memcpy(bg,gb,sizeof gb);memcpy(bn,nb,sizeof nb);
  int no[MAXB],ng[MAXB],nn[MAXB];
  clock_t t0=clock(); double T=60; long long it=0;
  while(1){
    if((it&0x1FF)==0){ double e=(double)(clock()-t0)/CLOCKS_PER_SEC; if(e>secs)break;
      double frac=fmod(e/secs*5.0,1.0); T=80.0*pow(0.25/80.0,frac); }
    it++;
    memcpy(no,ob,sizeof ob);memcpy(ng,gb,sizeof gb);memcpy(nn,nb,sizeof nb);
    int mv=rndi(100),i=rndi(S);
    if(mv<30){ int d=1+rndi(4); no[i]+=(rnd()&1)?d:-d; }
    else if(mv<45){ no[i]=rndi(MAXVAL+1); }
    else if(mv<70){ int d=1+rndi(3); ng[i]+=(rnd()&1)?d:-d; }
    else if(mv<78){ ng[i]=1+rndi(3*N/K+5); }
    else { int j=rndi(S); if(i==j) continue; int a=1+rndi(2); if(nn[i]<=a) continue; nn[i]-=a; nn[j]+=a; }
    int sc=score(no,ng,nn,S); if(sc>=(1<<28)) continue;
    int dE=sc-cur;
    if(dE<=0||rndd()<exp(-dE/T)){
      memcpy(ob,no,sizeof no);memcpy(gb,ng,sizeof ng);memcpy(nb,nn,sizeof nn); cur=sc;
      if(cur<best){best=cur;memcpy(bo,ob,sizeof ob);memcpy(bg,gb,sizeof gb);memcpy(bn,nb,sizeof nb);}
    }
  }
  fprintf(stderr,"best_missing=%d evals=%lld\n",best,it);
  printf("%d\n",best);
  for(int i=0;i<S;i++) printf("%d %d %d\n",bo[i],bg[i],bn[i]);
  int m=build(bo,bg,bn,S);
  fprintf(stderr,"nel=%d\n",m);
  FILE*f=fopen("cand.txt","w"); for(int i=0;i<m;i++) fprintf(f,"%d ",el[i]); fclose(f);
  return 0;
}
