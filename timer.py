# timer module
from __future__ import print_function
from time import clock

def timer(logger=print):
    def decorator(target):
        def wrapper(*args, **kwargs):
            initial = clock()
            target(*args, **kwargs)
            msg = "%s finished in %.2f seconds." % (target.__name__, (clock() - initial))
            return logger(msg)
        return wrapper
    return decorator
    
