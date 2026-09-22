/* Independent verifier (C): distinctness, nonnegativity, count, coverage of 1..N. */
#include <stdio.h>
#include <stdlib.h>
static int cmp(const void*a,const void*b){return *(const int*)a-*(const int*)b;}
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); int K=atoi(argv[2]), N=atoi(argv[3]);
  int *b=malloc(sizeof(int)*100000), n=0; long long v;
  while(fscanf(f,"%lld",&v)==1){ if(v<0){printf("FAIL: negative element %lld\n",v);return 1;} b[n++]=(int)v; }
  fclose(f);
  qsort(b,n,sizeof(int),cmp);
  for(int i=1;i<n;i++) if(b[i]==b[i-1]){ printf("FAIL: duplicate %d\n",b[i]); return 1; }
  if(n>K){ printf("FAIL: too many elements (%d > %d)\n",n,K); return 1; }
  int maxv=b[n-1];
  char*cov=calloc(maxv+2,1);
  for(int i=0;i<n;i++) for(int j=i+1;j<n;j++) cov[b[j]-b[i]]=1;
  int miss=0, firsthole=-1;
  for(int d=1;d<=N;d++) if(!cov[d]){ miss++; if(firsthole<0) firsthole=d; }
  int run=0; for(int d=1;d<=maxv;d++){ if(!cov[d]) break; run=d; }
  printf("elements read      : %d\n", n);
  printf("distinct elements  : %d (limit %d)\n",n,K);
  printf("all nonnegative    : yes\n");
  printf("range of elements  : [%d, %d]\n",b[0],maxv);
  printf("uncovered in 1..%d : %d\n",N,miss);
  printf("longest prefix 1..L fully covered: L = %d\n",run);
  printf("RESULT: %s\n", miss==0?"PASS":"FAIL");
  return miss==0?0:1;
}
