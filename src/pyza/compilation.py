'''
Created on 2010-03-24

@author: mdk
'''
import re, os, logging
from tempfile import mktemp
from pyza.config import TESTING_DIR
from pyza.executor import Executor, ExecutionError

log = logging.getLogger('Compilation')

class CompilatorExtensionError(Exception): pass

class CompilationError(Exception): pass

def compileGCC(ctx, filename, output, command):
    log.debug('C++ compiler: %s -> %s', filename, output)
    args = getattr(ctx, "cppArgs", [])
    args += [ '-O2', '--static', '-lm', filename, '-o', output ]
    log.debug("Run command gcc %s", str(args))
    e = Executor()
    e.command = command
    e.argv = args
    e.outputLimit = 10*1024*1024
    e.timeLimit = 30 * 1000 # 30 sec
    e.errput = '/dev/null'
    e.output = '/dev/null'
    status = 0
    try: e.run()
    except: status = -1
    else: status = e.returnCode
    log.debug('Compilation status %d, time %d', status, e.executionTime)
    if status != 0:
        log.info('Compiler return code: %d', e.returnCode)
        ctx.result.code = 'CE'
        raise CompilationError() 
    if not os.path.exists(output):
        log.info("Output file doesn't exists")
        ctx.result.code = 'CE'
        raise CompilationError()

def compileCpp(ctx, filename, output): 
    return compileGCC(ctx,filename,output,'/usr/bin/g++')

def compileAnsiC(ctx, filename, output): 
    return compileGCC(ctx,filename,output,'/usr/bin/gcc')

COMPILATORS = {
    'cpp|cxx' : compileCpp,
    'cc|c' : compileAnsiC,
}

def defaultCompile(ctx):
    """
        Uzywa pliku ctx.task.srcfile wraz z rozszerzeniem
        do znalezienia kompilatora i uruchamia tego co trzeba
    """
    srcfile = ctx.task.srcfile
    ext = srcfile[srcfile.find('.')+1:]
    
    # sprawdzamy, czy pasuje do patternu rozszerzen
    extpattern = re.compile(getattr(ctx, "extpattern", ".*"))
    if not re.match(extpattern, ext):
        ctx.result.code = 'EXT'
        raise CompilatorExtensionError()
    
    # szukamy kompilatora
    compilator = None
    for e,c in COMPILATORS.iteritems():
        extpattern = re.compile(e)
        if re.match(extpattern, ext):
            compilator = c
    if not callable(compilator):
        log.info('No matching compiler found for extension "%s"', ext)
        ctx.result.code = 'EXT'
        raise CompilatorExtensionError()
    
    # kompilujemy
    exefile = mktemp(suffix='.exe', dir=TESTING_DIR)
    log.debug('Compile task %s into file %s', str(ctx.task), exefile)
    compilator(ctx, srcfile, exefile)
    ctx.exefile = exefile
    log.debug('Compilation complete')
    
