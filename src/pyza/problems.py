'''
Created on 2010-03-20

@author: mdk
'''

class ProblemNotFoundException(Exception): pass

class ProblemManager: pass

_managers = []

def registerProblemManager(manager):
    """
    Rejestruje managera zadan i testow
    """
    _managers.append(manager)

def unregisterProblemManager(manager):
    """
    Wyrejestrowuje managera zadan i testow
    """
    try: _managers.remove(manager)
    except: pass

def _installProblem(pfile):
    pass

def findProblem(name):
    pass

def installUpdateProblem(task):
    problemid = task.problemid
    # find problem in local repo
    # and check local version
    
    # use problem managers to update
    # version if needed
    
    