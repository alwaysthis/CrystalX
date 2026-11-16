"""Optional C++ kernels; normal Python installation does not require a compiler."""
import os
import sys
from setuptools import Extension,setup

enabled=os.environ.get('CRYSTALX_BUILD_NATIVE')=='1' or 'build_ext' in sys.argv
flags=['/std:c++17','/O2','/fp:strict'] if sys.platform=='win32' else ['-std=c++17','-O3','-ffp-contract=off']
setup(ext_modules=[Extension('crystalx._native',
    sources=['native/module.cpp','native/material.cpp','native/bonds.cpp'],
    depends=['native/kernels.hpp'],language='c++',extra_compile_args=flags)] if enabled else [])
