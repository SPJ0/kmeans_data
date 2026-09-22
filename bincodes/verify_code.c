/* Second, independently written verifier (C).
   usage: verify_code <file> <count> <len> <mindist> */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
int main(int argc, char **argv){
  FILE *f = fopen(argv[1], "r");
  int want = atoi(argv[2]), L = atoi(argv[3]), D = atoi(argv[4]);
  char buf[512], w[4096][512]; int n = 0, bad = 0;
  while (fscanf(f, "%500s", buf) == 1) { strcpy(w[n++], buf); }
  fclose(f);
  for (int i = 0; i < n; i++) {
    if ((int)strlen(w[i]) != L) { printf("FAIL: string %d has length %zu\n", i, strlen(w[i])); bad = 1; }
    for (int k = 0; w[i][k]; k++)
      if (w[i][k] != '0' && w[i][k] != '1') { printf("FAIL: non-binary symbol in string %d\n", i); bad = 1; break; }
  }
  for (int i = 0; i < n; i++) for (int j = i+1; j < n; j++)
    if (!strcmp(w[i], w[j])) { printf("FAIL: strings %d and %d are equal\n", i, j); bad = 1; }
  if (n != want) { printf("FAIL: found %d strings, wanted exactly %d\n", n, want); bad = 1; }
  int mind = 1 << 30, pairs = 0;
  for (int i = 0; i < n; i++) for (int j = i+1; j < n; j++) {
    int d = 0; for (int k = 0; k < L; k++) if (w[i][k] != w[j][k]) d++;
    pairs++; if (d < mind) mind = d;
  }
  if (mind < D) { printf("FAIL: minimum distance %d < %d\n", mind, D); bad = 1; }
  printf("strings=%d  length=%d  pairs=%d  min distance=%d\n", n, L, pairs, mind);
  printf("RESULT: %s\n", bad ? "FAIL" : "PASS");
  return bad;
}
