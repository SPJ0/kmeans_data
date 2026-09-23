// SA over A = { (u*b mod m) + s_i + m*k_{i,b} : i<4, b in B }  (Singer B mod m).
// Moves: lift one element by +-m, shift a whole copy s_i by small delta, re-randomize u rarely no.
// Usage: lift_sa seed iters T0 [u]
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define TARGET 6166
#define K 4
int m,kB,B[64],Bu[64],n;
int s[K], kk[K][64], A[256];
int cnt[40000]; int covered;
static unsigned long long rs;
static inline unsigned rnd(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return (unsigned)(rs>>11); }
static inline void add(int d,int sg){ if(d<0)d=-d; if(d==0||d>TARGET) return; if(sg>0){ if(cnt[d]++==0) covered++; } else { if(--cnt[d]==0) covered--; } }
static inline int pos(int i,int j){ return Bu[j]+s[i]+m*kk[i][j]; }
void full(){ memset(cnt,0,sizeof cnt); covered=0; for(int i=0;i<n;i++) for(int j=i+1;j<n;j++) add(A[i]-A[j],1); }
void moveel(int idx,int nx){ int x=A[idx]; for(int j=0;j<n;j++) if(j!=idx){ add(x-A[j],-1); add(nx-A[j],1);} A[idx]=nx; }
int gcd(int a,int b){return b?gcd(b,a%b):a;}
int main(int argc,char**argv){
  FILE*f=fopen("out/singer31.txt","r"); if(fscanf(f,"%d",&m)!=1) return 1; kB=0; while(fscanf(f,"%d",&B[kB])==1) kB++; fclose(f);
  n=K*kB;
  rs=88172645463325252ULL ^ (unsigned long long)atoll(argv[1])*2654435761ULL; for(int i=0;i<10;i++) rnd();
  long iters=atol(argv[2]); double T0=atof(argv[3]);
  int bestall=0;
  for(int restart=0;;restart++){
    int u; if(argc>4) u=atoi(argv[4]); else do{u=1+rnd()%(m-1);}while(gcd(u,m)!=1);
    for(int j=0;j<kB;j++) Bu[j]=(int)((long)u*B[j]%m);
    int base[4]={0,1,4,6}; 
    for(int i=0;i<K;i++){ s[i]=base[i]*m + (int)(rnd()%m); for(int j=0;j<kB;j++) kk[i][j]=0; }
    for(int i=0;i<K;i++) for(int j=0;j<kB;j++) A[i*kB+j]=pos(i,j);
    full(); int cur=covered,best=cur;
    for(long it=0;it<iters;it++){
      double T=T0*(1.0-(double)it/iters)+0.02;
      int r=rnd()%100;
      if(r<85){ // lift move
        int i=rnd()%K,j=rnd()%kB; int d=(rnd()&1)?1:-1; int idx=i*kB+j; int nx=A[idx]+d*m;
        int dup=0; for(int t=0;t<n;t++) if(A[t]==nx){dup=1;break;} if(dup) continue;
        int before=covered; moveel(idx,nx); int delta=covered-before;
        if(delta>=0 || exp(delta/T)>(rnd()%1000000)/1e6){ kk[i][j]+=d; }
        else moveel(idx,nx-d*m);
      } else { // shift copy
        int i=rnd()%K; int d=(int)(rnd()%21)-10; if(!d) continue;
        int save[64]; for(int j=0;j<kB;j++) save[j]=A[i*kB+j];
        int before=covered;
        for(int j=0;j<kB;j++) moveel(i*kB+j,save[j]+d);
        // dup check
        int dup=0; for(int j=0;j<kB&&!dup;j++) for(int t=0;t<n;t++) if(t!=i*kB+j && A[t]==A[i*kB+j]){dup=1;break;}
        int delta=covered-before;
        if(!dup && (delta>=0 || exp(delta/T)>(rnd()%1000000)/1e6)) s[i]+=d;
        else for(int j=0;j<kB;j++) moveel(i*kB+j,save[j]);
      }
      if(covered>best) best=covered;
      if(covered==TARGET) break;
    }
    if(covered>bestall||covered==TARGET){ bestall=covered;
      printf("restart %d u %d covered %d\n",restart,u,covered); fflush(stdout);
      char fn[64]; sprintf(fn,"out/lift_best_%s.txt",argv[1]); FILE*g=fopen(fn,"w"); for(int t=0;t<n;t++) fprintf(g,"%d\n",A[t]); fclose(g);
      if(covered==TARGET){ printf("FOUND\n"); return 0; }
    }
  }
}
