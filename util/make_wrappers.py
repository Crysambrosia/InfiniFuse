import operator

def make_wrappers(cls, coercedMethods=[], nonCoercedMethods=[]):
    """Make wrapper methods for the given class, rewiring self.method -> self.value.method

    coercedMethods    : return value of same type as self
    nonCoercedMethods : return something else
    
    This reduces the likeliness of errors greatly, and should make code easier to understand
    Checks if method in dir(operator), for proper reverse operator handling
    ( when something is NotImplemented )
    """

    for method in coercedMethods:
        if method in dir(operator):
            def wrapper(self, *args, _method=method, **kwargs):
                return type(self)( getattr(operator, _method)(self.value, *args, **kwargs) )
            setattr(cls, method, wrapper)
        else:
            def wrapper(self, *args, _method=method, **kwargs):
                return type(self)( getattr(self.value, _method)(*args, **kwargs) )
            setattr(cls, method, wrapper)
    
    for method in nonCoercedMethods:
        if method in dir(operator):
            def wrapper(self, *args, _method=method, **kwargs):
                return getattr(operator, _method)(self.value, *args, **kwargs)
            setattr(cls, method, wrapper)
        else:
            def wrapper(self, *args, _method=method, **kwargs):
                return getattr(self.value, _method)(*args, **kwargs)
            setattr(cls, method, wrapper)
    
    # This makes sure ABC doesn't refuse instanciation
    cls.__abstractmethods__ = cls.__abstractmethods__.difference(coercedMethods, nonCoercedMethods)