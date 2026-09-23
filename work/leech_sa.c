// SA over structured sets A = U_i ( rep(u*B + c_i mod m) + t_i ), i=0..K-1
// objective: number of d in [1,TARGET] covered. Usage: leech_sa seed iters
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define TARGET 6166
int m, kB, B[64], K=4;
int u, c[8], t[8];
static unsigned long long rs;
static inline unsigned rnd(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return (unsigned)(rs>>11); }
int A[512], nA;
unsigned char cov[1<<16];
int build(){
  nA=0;
  for(int i=0;i<K;i++) for(int j=0;j<kB;j++) A[nA++]= (int)(((long)u*B[j]+c[i])%m) + t[i];
  return nA;
}
int score(){
  build();
  memset(cov,0,TARGET+1);
  int s=0;
  for(int i=0;i<nA;i++) for(int j=0;j<nA;j++){ int d=A[i]-A[j]; if(d>0 && d<=TARGET && !cov[d]){cov[d]=1;s++;} }
  return s;
}
int prefix(){ int L=0; while(L<TARGET && cov[L+1]) L++; return L; }
int gcd(int a,int b){return b?gcd(b,a%b):a;}
int main(int argc,char**argv){
  FILE*f=fopen(argc>3?argv[3]:"out/singer31.txt","r"); if(fscanf(f,"%d",&m)!=1) return 1; kB=0; while(fscanf(f,"%d",&B[kB])==1) kB++; fclose(f);
  rs = 88172645463325252ULL ^ (unsigned long long)atoll(argv[1])*2654435761ULL; for(int i=0;i<10;i++) rnd();
  long iters=atol(argv[2]);
  int best_all=0;
  for(int restart=0;;restart++){
    do{u=1+rnd()%(m-1);}while(gcd(u,m)!=1);
    int base[4]={0,1,4,6}; if(rnd()&1){base[1]=2;base[2]=5;}
    for(int i=0;i<K;i++){ c[i]=rnd()%m; t[i]=base[i]*m + (int)(rnd()%41)-20; }
    int cur=score(), best=cur;
    double T0=3.0;
    for(long it=0;it<iters;it++){
      double T=T0*(1.0-(double)it/iters)+0.05;
      int su=u, sc[8], st[8]; memcpy(sc,c,sizeof c); memcpy(st,t,sizeof t);
      int r=rnd()%10, i=rnd()%K;
      if(r<3) c[i]=rnd()%m;
      else if(r<5) c[i]=(c[i]+ (int)(rnd()%21)-10 + m)%m;
      else if(r<8) t[i]+= (int)(rnd()%11)-5;
      else if(r<9) t[i]+= (int)(rnd()%201)-100;
      else { do{u=1+rnd()%(m-1);}while(gcd(u,m)!=1); }
      int s=score();
      if(s>=cur || exp((s-cur)/T) > (rnd()%1000000)/1e6){ cur=s; if(s>best){best=s;} }
      else { u=su; memcpy(c,sc,sizeof c); memcpy(t,st,sizeof t); }
    }
    score();
    if(cur>best_all || cur==TARGET){ best_all=cur;
      printf("restart %d score %d prefix %d u %d | c %d %d %d %d | t %d %d %d %d\n",restart,cur,prefix(),u,c[0],c[1],c[2],c[3],t[0],t[1],t[2],t[3]); fflush(stdout);
      if(cur==TARGET){ FILE*g=fopen("out/found_leech.txt","w"); for(int k=0;k<nA;k++) fprintf(g,"%d\n",A[k]); fclose(g); return 0; }
    }
  }
}
