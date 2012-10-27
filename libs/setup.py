#setup.py
from distutils.core import setup
from distutils.extension import Extension
import os.path
import sys

include_dirs = ["/usr/include/boost","."]
libraries=["boost_python"]
library_dirs=['/usr/lib']

files = ["executor.cpp"]

setup(name="executor",    
      ext_modules=[
                    Extension("executor",files,
                    library_dirs=library_dirs,
                    libraries=libraries,
                    include_dirs=include_dirs,
                    depends=[]),
                    ]
     )
