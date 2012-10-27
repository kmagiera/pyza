
#include <cstdio>
#include <ctime>
#include <cstdlib>
#include <unistd.h>

const char* fname = "/tmp/kaszanka";

main() {
	int a = 9;
	int res = 0;
	//for (int i=100;i>-2;i--) res += res / i;
	printf("%d %d %d\n", (int)sizeof(unsigned int), (int)sizeof(unsigned long), (int)sizeof(size_t));
	printf("Fname %p\n", fname);
	FILE* fp = fopen(fname, "w");
	printf("X Fileno %d\n", fileno(fp));
	fprintf(fp, "Kaszanka\n");
	fflush(fp);
	fclose(fp);
}
/*
  unsigned long r15;
  unsigned long r14;
  unsigned long r13;
  unsigned long r12;
  unsigned long rbp;
  unsigned long rbx;
  unsigned long r11;
  unsigned long r10;
  unsigned long r9;
  unsigned long r8;
  unsigned long rax;
  unsigned long rcx;
  unsigned long rdx;
  unsigned long rsi;
  unsigned long rdi;
  unsigned long orig_rax;
  unsigned long rip;
  unsigned long cs;
  unsigned long eflags;
  unsigned long rsp;
  unsigned long ss;
  unsigned long fs_base;
  unsigned long gs_base;
  unsigned long ds;
  unsigned long es;
  unsigned long fs;
  unsigned long gs;
*/
