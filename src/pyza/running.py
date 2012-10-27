'''
Created on 2010-03-19

@author: mdk
'''

from pyza.executor import Executor
from pyza.executor import TimeLimitError
import logging, os

DEFAULT_TIME_LIMIT = -1     # UNLIMITED
DEFAULT_MEM_LIMIT = -1      # UNLIMITED
DEFAULT_OUTPUT_LIMIT = -1   # UNLIMITED    

log = logging.getLogger('Running')

class ExecutionError(Exception): pass

class IllegalSyscallError(Exception): pass

LEGAL_SYSCALLS = set([0,1,63,12,14,205,5,9,11,231,16,13,89,132,201,35,158,186,234])

def syscallCallback(evt):
    global log
    if evt not in LEGAL_SYSCALLS:
    	log.error("Illegal syscall %d" % evt)
        raise IllegalSyscallError()

def defaultRun(ctx):
    e = Executor()
    e.command = ctx.exefile
    e.input = ctx.inputfile
    e.output = ctx.outputfile
    e.errput = '/dev/null'
    timeLimit = getattr(ctx, 'timeLimit', DEFAULT_TIME_LIMIT)
    if timeLimit > -1: e.timeLimit = int(timeLimit * 1000)
    e.memoryLimit = getattr(ctx, 'memoryLimit', DEFAULT_MEM_LIMIT)
    e.outputLimit = getattr(ctx, 'outputLimit', DEFAULT_OUTPUT_LIMIT)
    e.callback = syscallCallback
    res = 'OK'
    log.debug('Run programm %s on %s (limits %d,%d,%d)', ctx.exefile, 
              ctx.inputfile, e.timeLimit, e.memoryLimit, e.outputLimit)
    try:
        e.run()
        if e.returnCode != 0:
            res = 'RTE'
    except TimeLimitError:
        log.exception('Time Limit Exceeded')
        res = 'TLE'
    except IllegalSyscallError:
        log.exception('Illegal Syscall')
        res = 'ILL'
    except:
        log.exception('Running error')
        res = 'RTE'
    # set some of results in CTX
    ctx.returnCode = e.returnCode
    ctx.executionTime = '%.3f' % (e.executionTime / 1000.0)
    if res != 'OK':
        ctx.result.code = res
        ctx.result.cases.append((os.path.basename(ctx.inputfile), ctx.executionTime, res))
        raise ExecutionError()
