# http://askawizard.blogspot.com/2008/09/decorators-python-saga-part-2_28.html
class memoize:
    def __init__(self, cache = None):
        self.cache = cache
    def __call__(self, function):
        return Memoized(function, self.cache)

class Memoized:
    def __init__(self, function, cache = None):
        if cache is None: cache = {}
        self.function = function
        self.cache = cache
    def __call__(self, *args):
        if args not in self.cache:
            self.cache[args] = self.function(*args)
        return self.cache[args]
