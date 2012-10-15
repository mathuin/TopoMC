# timer module
from __future__ import print_function
from time import clock

def timer(logger=print):
    def decorator(target):
        def wrapper(*args, **kwargs):
            initial = clock()
            retval = target(*args, **kwargs)
            msg = "%s finished in %.2f seconds." % (target.__name__, (clock() - initial))
            logger(msg)
            return retval
        return wrapper
    return decorator
    
