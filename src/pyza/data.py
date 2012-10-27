'''
Created on Mar 25, 2010

@author: mdk
'''
import os
from pyza.config import PROBLEMS_DIR
from pyza.testing import defaultTesting
from pyza.compilation import defaultCompile
from pyza.running import defaultRun
from pyza.comparators import defaultDiff

class Result:
    """
    Attributes:
        code -- ogolny wynik calego testowania
        cases -- lista podwynikow
    """
    def __init__(self):
        self.code = None
        self.cases = []
    
    def __str__(self):
        return str(self.code)

class Limits: pass

class Task:
    def __init__(self, problemid = None, userid = None, srcfile = None):
        self.problemid = problemid
        self.userid = userid
        self.srcfile = srcfile
    def __str__(self):
        return 'Task[%s]' % str(getattr(self,"id","ANONYMOUS"))

class TestingContext:
    """
    Attributes:
        id -- identyfikator
        problemid -- identyfikator zadania
        userid -- identyfikator uzytkownika
        result -- wynik
        testing -- funkcja testujaca cale zadanie
        compile -- funkcja kompilujaca rozwiazanie
        run -- funkcja testujaca pojedynczy case
        diff -- funkcja porownujaca wyjscie pojedynczego testu
    """
    
    def __init__(self, task):
        self.task = task
        self.problemdir = os.path.join(PROBLEMS_DIR, str(task.problemid))
        self.result = Result()
        self.limits = Limits()
        self.testing = defaultTesting
        self.compile = defaultCompile
        self.run = defaultRun
        self.diff = defaultDiff
    
    def __str__(self):
        return 'TestingContext[problem=%s,id=%s,user=%s,result=%s]' % \
                    (str(self.problemid),str(self.id),
                     str(self.userid),str(self.result))

