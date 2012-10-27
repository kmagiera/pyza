import executor, sys

e = executor.Executor()
e.flags = executor.TRACE_CHILDS
e.command = "/usr/bin/g++"
e.argv = [ '-O2', '--static', '-lm', '/home/eaiiegrp/kmagiera/pyza/libs/dupa.cpp', '-o', '/home/eaiiegrp/kmagiera/pyza/libs/dupa.exe' ]
e.run()

sys.stderr.write("Return code: %d\n" % e.returnCode)


