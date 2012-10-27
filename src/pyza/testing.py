from fnmatch import fnmatch
from os import path as PATH
from pyza.config import TESTING_DIR
from tempfile import mktemp
import logging
import os

class OutFileNotFoundError(Exception): pass

class NoTestCasesError(Exception): pass

log = logging.getLogger('Testing')

def setLimits(ctx, filename):
    '''
        Wczytuje limity z podanego pliku. Plik taki
        moze byc zwyklym skrytem python. Wszystkie zadeklarowane
        zmienne globalne zostana ustawione w kontekscie testu.
        Skrypt moze korzystac z globalnej zmiennej ctx oznaczajacej
        kontekst.
    '''
    if not PATH.exists(filename): return
    locals = {}
    execfile(filename, {'ctx': ctx}, locals)
    for k,v in locals.iteritems():
        setattr(ctx, k, v)

def defaultTesting(ctx):
    """
        Operacja wykorzystuje wszystkie pliki z rozszerzeniem
        in do odpalenia skompilowanego problemu podajac pliki
        in na standardowe wejscie. Kazdy plik in powinien
        miec odpowiadajacy plik out z ktorym porownywane bedzie
        wyjscie programu.
        Dodatkowo mozliwe jest zapisanie limitow na wszystkie
        testy w pliku global.lim
    """
    cases = []
    for file in os.listdir(ctx.problemdir):
        if fnmatch(file, '*.in'):
            cases.append(file[:-2])
    if len(cases) == 0:
        log.warning('No test cases found!')
        raise NoTestCasesError()
    glimits = PATH.join(ctx.problemdir, 'global.lim')
    
    # przystepujemy do testowania
    cases.sort()
    ctx.outputfile = mktemp(dir=TESTING_DIR)
    res = 'OK'
    for i, case in enumerate(cases):
        log.debug('Testing case %d (%s)', i, case[:-1])
        ctx.caseid = i
        ctx.inputfile = PATH.join(ctx.problemdir, case + 'in')
        ctx.difffile = PATH.join(ctx.problemdir, case + 'out')
        limitsfile = PATH.join(ctx.problemdir, case + 'lim')
        if not PATH.exists(ctx.difffile):
            raise OutFileNotFoundError()
        # ustawiamy limity najpierw globalne, pozniej lokalne
        setLimits(ctx, glimits)
        setLimits(ctx, limitsfile)
        try:
            ctx.run(ctx)
            ctx.diff(ctx)
        except: pass
        if ctx.result.code != 'OK': res = ctx.result.code
    ctx.result.code = res;

