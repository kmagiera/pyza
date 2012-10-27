'''
Created on 2010-03-24

@author: mdk
'''

from executor import Executor
import logging, os

log = logging.getLogger('Comparators')

class WrongAnswerError(Exception): pass

def defaultDiff(ctx):
    log.debug('Comparing %s and %s', ctx.outputfile, ctx.difffile)
    e = Executor()
    e.command = '/usr/bin/diff'
    e.argv = [ '-bB', ctx.outputfile, ctx.difffile ]
	
	# use local judge
    localcmp = os.path.join(ctx.problemdir, 'judge')
    if os.path.isfile(localcmp):
        log.debug('Use local judge')
        e.command = localcmp
        e.argv = [ ctx.outputfile, ctx.inputfile, ctx.difffile ]

    e.timeLimit = 20 * 1000 # 20 sec limit
    e.output = '/dev/null'
    e.errput = '/dev/null'
    status = 0;
    try: e.run()
    except: status = -1;
    else: status = e.returnCode
    if status != 0:
        ctx.result.code = 'WA'
        ctx.result.cases.append((os.path.basename(ctx.inputfile), ctx.executionTime, 'WA'))
        raise WrongAnswerError()
    ctx.result.cases.append((os.path.basename(ctx.inputfile), ctx.executionTime, 'OK'))
    ctx.result.code = 'OK'
