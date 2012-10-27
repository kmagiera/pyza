#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <sys/user.h>
#include <linux/unistd.h>
#include <sys/time.h>
#include <sys/syscall.h>
#include <sys/resource.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <signal.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <vector>

# if defined __x86_64__
#  define ORIG_REG orig_rax
# elif defined __i386__
#  define ORIG_REG orig_eax
# else
#  warning This machine appears to be neither x86_64 nor i386.
# endif

#define ERR(msg) fprintf(stderr, "%s\n", msg); throw 1
#define PALL PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE \
	| PTRACE_O_TRACEEXEC | PTRACE_O_TRACEVFORKDONE | PTRACE_O_TRACEEXIT

const char* cmd = "/usr/bin/java";
char* args[] = { "/usr/bin/java", "Dupa" };

void run() {
	pid_t proc,nproc = -1,bpid;
	int status,evt;
	bool firstExec = false;
	struct user_regs_struct regs;

	if ((proc = vfork()) == 0) {
		/* ten proces bedzie sledzony: */
		if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) != 0) {
			_exit(5);
		}
		/* wywolujemy program */
		execv("/usr/bin/java", args);
		_exit(3);
	} else if (proc > 0) {
		int childs = 1;
		ptrace(PTRACE_SETOPTIONS,proc,NULL,PALL);
	
		while (1) {
			evt = 0;
			//printf("WAIT\n");
			/* czekamy na kolejne zatrzymanie przez ptrace */
			if ((bpid = wait4(-1, &status, WUNTRACED|__WALL, 0)) <= 0) {
				ERR("Wait err");
			}
			//printf("PID %d\n", (int)bpid);

			if (WIFSTOPPED(status) && WSTOPSIG(status) == SIGTRAP) {
				/* pobieramy wartosci rejestrow */
				//printf("Trapped %d\n", (int)bpid);
				evt = (status >> 16) & 0xffffff;
				if (evt) {
					printf("EVT %d [%d, %d, %d]\n", evt, PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK, PTRACE_EVENT_CLONE);
					ptrace(PTRACE_GETEVENTMSG,bpid,NULL,&nproc);
					printf("NPROC %d\n", (int)nproc);
					if (evt == PTRACE_EVENT_FORK || evt == PTRACE_EVENT_VFORK || evt == PTRACE_EVENT_CLONE) childs++;
				}
				
				if (ptrace(PTRACE_GETREGS, bpid, NULL, &regs) != 0) {
					ERR("Ptrace getregs fault");
				}
				long int eax = regs.ORIG_REG;

				if (!firstExec) {
					/* czekamy na pierwszy execv */
					if (eax == SYS_execve)
						firstExec = true;
				} else {
					if (eax == __NR_open) {
						union u {
								long int val;
								char chars[sizeof(long)];
						}data;
						long addr = regs.ebx;
						char buf[256] = "";
						char *ptr = buf;
						while (addr != 0) {
							data.val = ptrace(PTRACE_PEEKDATA, bpid, addr, NULL);
							addr += sizeof(long);
							for (int i=0;i<sizeof(long);i++) if (data.chars[i]==0) addr = 0;
							memcpy(ptr, data.chars, 4);
							ptr += sizeof(long);
						}
						printf("Open('%s') = %ld\n", buf, regs.eax);
					}
					//printf("Syscall %d\n", (int)eax);
				}

			} else if (WIFSTOPPED(status)) {
				printf("Stopped %d\n", (int)bpid);
			} else if (WIFEXITED(status)) {
				printf("Exited %d\n", (int)bpid);
				if (--childs) continue;
				break;
			} else { /* signalled */
				printf("SIGNALLED\n");
			}
			
			/* puszczamy proces sledzony dalej */
			if (ptrace(PTRACE_SYSCALL, bpid, NULL, 0) != 0) {
				perror("DUPA");
				ERR("Ptrace syscall fault");
			}
		}
	} else {
		/* nie moze wykonac fork'a */
		ERR("FORK");
	}
}

main() {
	run();
}

