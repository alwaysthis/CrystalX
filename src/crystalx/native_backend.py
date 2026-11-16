"""Load optional kernels once; never compile code during application startup."""
import logging
import os
from importlib import import_module

def _load():
    if os.environ.get('CRYSTALX_DISABLE_NATIVE')=='1': return None
    try:
        module=import_module('crystalx._native')
    except ModuleNotFoundError as error:
        if error.name!='crystalx._native':
            logging.getLogger(__name__).warning('C++ dependency unavailable; using Python: %s',error)
        return None
    except ImportError as error:
        logging.getLogger(__name__).warning('Cannot load C++ kernels; using Python: %s',error)
        return None
    if getattr(module,'API_VERSION',None)!=2:
        logging.getLogger(__name__).warning('C++ kernel API mismatch; rebuild extension. Using Python.')
        return None
    return module

kernels=_load()
