#include <cstdio>
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
#include <boost/python.hpp>
#include <vector>
#include <algorithm>

# if defined __x86_64__
#  define ORIG_REG orig_rax
#  define REG_ARG1 rdi
#  define REG_ARG2 rsi
# elif defined __i386__
#  define ORIG_REG orig_eax
#  define REG_ARG1 ebx
#  define REG_ARG2 ecx
# else
#  warning This machine appears to be neither x86_64 nor i386.
# endif

#define PYZA_CLOSE_STDIN		(1<<0)
#define PYZA_CLOSE_STDOUT		(1<<1)
#define PYZA_CLOSE_STDERR 		(1<<2)
#define PYZA_TRACE_CHILDS		(1<<3)

using namespace boost::python;

namespace pyza {

  /* Exceptions */

  class ExecutionError {
  public:
    std::string message;
    ExecutionError(const std::string& msg) : message(msg) {}
  };
  PyObject* ExecutionErrorType = NULL;

  class TimeLimitError {
  };
  PyObject* TimeLimitErrorType = NULL;

  class RuntimeError {
  public:
    std::string message;
    RuntimeError(const std::string& msg) : message(msg) {}
  };
  PyObject* RuntimeErrorType = NULL;

  /* Executor */

  class Executor {
  private:
    void cleanup();
  public:
    Executor();
    void run();
    tuple getSyscallArgs();
    int memoryLimit , outputLimit, timeLimit; // memoryLimit (bytes), outputLimit(bytes), timeLimit(bytes)
    int returnCode, executionTime;
    int flags;
    std::string command;
    object argv;
    object callback;
    object input, output, errput;
		
    /* zajetosc poczatkowa */
    struct rusage startusage;
		
    /* chwilowe dane */
    struct user_regs_struct regs;
    pid_t pid, proc;
  };

  Executor::Executor() {
    this->memoryLimit = -1;
    this->outputLimit = -1;
    this->timeLimit = -1;
    this->flags = 0;
  }

  void Executor::run() {
    int status;
    bool firstExec = false;

    /* construct arguments vector */
    std::vector<char*> cargv;
    std::vector<std::string> eargv;
    cargv.push_back((char*)command.c_str());
    if (argv.ptr() != Py_None) {
      int l = len(argv);
      for (int i=0;i<l;i++) {
        extract<std::string> str(argv[i]);
        eargv.push_back(str());
        cargv.push_back((char*)eargv[i].c_str());
      }
    }
    cargv.push_back(NULL);
	
    /* convert filenames into C strings */
    const char* file_input = NULL;
    const char* file_output = NULL;
    const char* file_errput = NULL;
    if (input.ptr() != Py_None) {
      extract<std::string> str(input);
      file_input = str().c_str();
      eargv.push_back(str);
    }
    if (output.ptr() != Py_None) {
      extract<std::string> str(output);
      file_output = str().c_str();
      eargv.push_back(str);
    }
    if (errput.ptr() != Py_None) {
      extract<std::string> str(errput);
      file_errput = str().c_str();
      eargv.push_back(str);
    }

    /* zapamietujemy startowy rusage */
    if (getrusage(RUSAGE_CHILDREN, &startusage)) {
      throw ExecutionError("Could not get starter rusage");
    }

    if ((proc = vfork()) == 0) {

      /* zamykamy wejscia / wyjscia */
      /*if (data->flags & PLF_CLOSESTDIN)
        if (close(STDIN_FILENO) != 0)
        _exit(2);

        if (data->flags & PLF_CLOSESTDOUT)
        if (close(STDOUT_FILENO) != 0)
        _exit(2);

        if (data->flags & PLF_CLOSESTDERR)
        if (close(STDERR_FILENO) != 0)
        _exit(2);*/

      /*  przekierowanie wyjscia / wejscia */
      int fd;
      if (file_input) {
        fd = open(file_input, O_RDONLY);
        if (fd < 0) _exit(2);
        dup2(fd, STDIN_FILENO);
      }
      if (file_output) {
        fd = open(file_output, O_RDWR | O_CREAT | O_TRUNC, S_IWUSR | S_IRUSR);
        if (fd < 0) _exit(2);
        dup2(fd, STDOUT_FILENO);
      }
      if (file_errput > 0) {
        fd = open(file_errput, O_RDWR | O_CREAT | O_TRUNC, S_IWUSR | S_IRUSR);
        if (fd < 0) _exit(2);
        dup2(fd, STDERR_FILENO);
      }

      /* ustawiamy limit pamieci wirtualnej jesli byl wskazany */
      if (memoryLimit != -1) {
        struct rlimit vmlimit;
        if (getrlimit(RLIMIT_AS, &vmlimit) != 0) {
          _exit(1);
        }
        vmlimit.rlim_cur = memoryLimit;
        if (setrlimit(RLIMIT_AS, &vmlimit) != 0) {
          _exit(1);
        }
      }

      // TODO: mozna jeszcze ustawiac limity na stos

      /* limit wyjscia (laczna wielkosc wszystkich plikow po ktorych piszemy) */
      if (outputLimit != -1) {
        struct rlimit foutlimit;
        if (getrlimit(RLIMIT_FSIZE, &foutlimit) != 0) {
          _exit(3);
        }
        foutlimit.rlim_cur = outputLimit;
        if (setrlimit(RLIMIT_FSIZE, &foutlimit) != 0) {
          _exit(3);
        }
      }

      /* ustawiamy limit czasu wkonania (jesli byl wybrany) */
      if (timeLimit != -1) {
        struct rlimit tmlimit;
        if (getrlimit(RLIMIT_CPU, &tmlimit) != 0) {
          _exit(4);
        }
        tmlimit.rlim_cur = (timeLimit + 1000) / 1000;
        if (setrlimit(RLIMIT_CPU, &tmlimit) != 0) {
          _exit(4);
        }
      }

      /* ten proces bedzie sledzony: */
      if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) != 0) {
        _exit(5);
      }

      /* wywolujemy program */
      execv(command.c_str(), &(cargv.front()));
      _exit(3);
    } else if (proc > 0) {

      int waitflags = 0;
      if (flags & PYZA_TRACE_CHILDS) {
        waitflags = WUNTRACED | __WALL;
        ptrace(PTRACE_SETOPTIONS, proc, NULL, PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE
               | PTRACE_O_TRACEEXEC | PTRACE_O_TRACEVFORKDONE | PTRACE_O_TRACEEXIT);
      }
		
      try {
        while (1) {
          /* czekamy na kolejne zatrzymanie przez ptrace */
          if ((pid = wait4(-1, &status, waitflags, 0)) <= 0) {
            throw ExecutionError("Wait fault");
          }

          if (WIFSTOPPED(status) && WSTOPSIG(status) == SIGTRAP) {
            /* pobieramy wartosci rejestrow */
            if (ptrace(PTRACE_GETREGS, pid, NULL, &regs) != 0) {
              throw ExecutionError("Ptrace getregs fault");
            }
					
            if (!firstExec) {
              /* czekamy na pierwszy execv */
              if (regs.ORIG_REG == SYS_execve)
                firstExec = true;
            } else {
              if (callback.ptr() != Py_None)
                callback(regs.ORIG_REG);
            }

          } else if (WIFSTOPPED(status)) {
            int stopsig = WSTOPSIG(status);
            if (stopsig == SIGXCPU) {
              throw TimeLimitError();
            } else if (stopsig == SIGXFSZ) {
              throw RuntimeError("OutputSizeLimit");
            } else if (stopsig == SIGSEGV) {
              throw RuntimeError("SIGSEGV");
            } else if (stopsig == SIGFPE) {
              throw RuntimeError("SIGFPE");
            }
          } else if (WIFEXITED(status)) {
            if (!firstExec) {
              throw ExecutionError("Initial error");
            }
            returnCode = WEXITSTATUS(status);
            if (pid == proc) break;
            else continue;
          } else { /* signalled */
            throw RuntimeError("SIGNALLED");
          }
				
          /* puszczamy proces sledzony dalej */
          if (ptrace(PTRACE_SYSCALL, pid, NULL, NULL) != 0) {
            throw ExecutionError("Ptrace syscall fault");
          }
        }
      } catch (const TimeLimitError& ex) {
        cleanup();
        throw ex;
      }
      catch (const RuntimeError& ex) {
        cleanup();
        throw ex;
      } catch (const ExecutionError& ex) {
        cleanup();
        throw ex;
      } catch(const error_already_set& ex) {
        cleanup();
        throw ex;
      }
      cleanup();
      if (timeLimit > -1 && executionTime > timeLimit) {
        throw TimeLimitError();
      }
    } else {
      /* nie moze wykonac fork'a */
      throw ExecutionError("Fork error");
    }

    return;
  }

  void Executor::cleanup() {
    struct rusage usage;
    ptrace(PTRACE_KILL, pid, 0, 0);
    waitpid(pid, NULL, 0);
    ptrace(PTRACE_KILL, proc, 0, 0);
    waitpid(proc, NULL, 0);
    getrusage(RUSAGE_CHILDREN, &usage);
    executionTime = (usage.ru_utime.tv_sec - startusage.ru_utime.tv_sec) * 1000
      + (usage.ru_utime.tv_usec - startusage.ru_utime.tv_usec) / 1000;
    //fprintf(stderr, "Execution time %d\n", executionTime);
  }

  static void readFromAddr(pid_t pid, unsigned long addr, char* buf, size_t buflen) {
    union {
      long val;
      char chars[sizeof(long)+1];
    } data;
    data.chars[sizeof(long)] = 0;
    size_t off = 0;
    while (off < buflen) {
      data.val = ptrace(PTRACE_PEEKDATA, pid, addr + off, NULL);
      memcpy(buf+off, data.chars, (buflen-off)<sizeof(long)?(buflen-off):sizeof(long));
      for (size_t i=0;i<sizeof(long);i++) if (buf[off+i]==0) break;
      off += sizeof(long);
    }
  }

  tuple Executor::getSyscallArgs() {
    //fprintf(stderr, "Regs1: [%lu] %lu %lu %lu %lu %lu\n",regs.orig_rax,regs.rdi,regs.rsi,regs.rdx,regs.rcx,regs.rbx);
    switch (regs.ORIG_REG) {
	
    case __NR_open:
      char fname[256];
      readFromAddr(pid, regs.REG_ARG1, fname, sizeof(fname));
      return make_tuple(fname, regs.REG_ARG2);
	
    case __NR_write:
      /* narazie zwacamy file descriptor */
      return make_tuple(regs.REG_ARG1);
	
    case __NR_read:
      /* narazie zwracamy tylko file descriptor */
      return make_tuple(regs.REG_ARG1);
	
    }
    return make_tuple();
  }

  void executionErrorTrans(const ExecutionError& e) {
    boost::python::object pyex(e);
    PyErr_SetObject(ExecutionErrorType, pyex.ptr());
  }

  void timeLimitErrorTrans(const TimeLimitError& e) {
    boost::python::object pyex(e);
    PyErr_SetObject(TimeLimitErrorType, pyex.ptr());
  }
  void runtimeErrorTrans(const RuntimeError& e) {
    boost::python::object pyex(e);
    PyErr_SetObject(RuntimeErrorType, pyex.ptr());
  }

} /* namespace */

BOOST_PYTHON_MODULE(executor)
{
  // Create the Python type object for our extension class and define __init__ function.
  class_<pyza::Executor>("Executor", 
                         "Attributes:\n"
                         " callback - callable function with one argument\n"
                         " memoryLimit - limit for virtual memory in bytes (-1 UNLIMITED)\n"
                         " outputLimit - limit for output files in bytes (-1 UNLIMITED)\n"
                         " timeLimit - execution time limit in Milliseconds (-1 UNLIMITED)\n"
                         " returnCode - code returned by executed process\n"
                         " executionTime - execution time in Milliseconds\n"
                         " command - command to call\n"
                         " argv - list of arguments\n"
                         " input - input file bounded to STDIN\n"
                         " output - output file bounded to STDOUT\n"
                         " errput - file bounded to stderr output\n"
                         ).def("run", &pyza::Executor::run)
    .def("getSyscallArgs", &pyza::Executor::getSyscallArgs)
    .def_readwrite("callback", &pyza::Executor::callback)
    .def_readwrite("memoryLimit", &pyza::Executor::memoryLimit)
    .def_readwrite("outputLimit", &pyza::Executor::outputLimit)
    .def_readwrite("timeLimit", &pyza::Executor::timeLimit)
    .def_readonly("returnCode", &pyza::Executor::returnCode)
    .def_readonly("executionTime", &pyza::Executor::executionTime)
    .def_readonly("pid", &pyza::Executor::pid)
    .def_readwrite("command", &pyza::Executor::command)
    .def_readwrite("argv", &pyza::Executor::argv)
    .def_readwrite("flags", &pyza::Executor::flags)
    .def_readwrite("input", &pyza::Executor::input)
    .def_readwrite("output", &pyza::Executor::output)
    .def_readwrite("errput", &pyza::Executor::errput);
    
  // Constants
  scope().attr("CLOSE_STDIN") = PYZA_CLOSE_STDIN;
  scope().attr("CLOSE_STDOUT") = PYZA_CLOSE_STDOUT;
  scope().attr("CLOSE_STDERR") = PYZA_CLOSE_STDERR;
  scope().attr("TRACE_CHILDS") = PYZA_TRACE_CHILDS;
    
  // Exceptions
  class_<pyza::ExecutionError> ExecutionErrorCls("ExecutionError", init<std::string>());
  ExecutionErrorCls.def_readwrite("message", &pyza::ExecutionError::message);
  pyza::ExecutionErrorType = ExecutionErrorCls.ptr();
  register_exception_translator<pyza::ExecutionError>(&pyza::executionErrorTrans);
    
  class_<pyza::TimeLimitError> TimeLimitErrorCls("TimeLimitError");
  pyza::TimeLimitErrorType = TimeLimitErrorCls.ptr();
  register_exception_translator<pyza::TimeLimitError>(&pyza::timeLimitErrorTrans);
    
  class_<pyza::RuntimeError> RuntimeErrorCls("RuntimeError", init<std::string>());
  RuntimeErrorCls.def_readwrite("message", &pyza::RuntimeError::message);
  pyza::RuntimeErrorType = RuntimeErrorCls.ptr();
  register_exception_translator<pyza::RuntimeError>(&pyza::runtimeErrorTrans);
    
}


