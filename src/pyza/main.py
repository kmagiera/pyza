'''
Created on 2010-03-21

@author: mdk
'''

from pyza.data import TestingContext
from pyza.emailAgent import getTask, saveResult
import logging, os
from pyza.config import TESTING_DIR

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('Testing')

taskReceiver = getTask
resultSaver = saveResult

def cleanup():
    for file in os.listdir(TESTING_DIR):
        fn = os.path.join(TESTING_DIR, file)
        try:
            if os.path.isdir(fn): os.rmdir(fn)
            else: os.remove(fn)
        except: pass

def testingThread():
    while True:
        cleanup()
        task = None
        try: task = taskReceiver()
        except KeyboardInterrupt:
        	log.debug("Finishing")
        	return
        except: log.exception('Error while getting new task')
        else:
            ctx = TestingContext(task)
            try:
                ctx.compile(ctx)
                ctx.testing(ctx)
            except KeyboardInterrupt: raise KeyboardInterrupt
            except: log.exception('Task processing error')
            try: resultSaver(task, ctx.result)
            except KeyboardInterrupt: raise KeyboardInterrupt
            except: log.exception('Result saving error')

if __name__ == "__main__":
    testingThread()
    
