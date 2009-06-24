def exceptional(func,alt_return=None,alt_exceptions=(Exception,),final=None,catch=None):
    """turns exceptions into alternative return value"""
    def _exceptional(*args,**kwargs):
        try:
            try: return func(*args,**kwargs)
            except alt_exceptions:
                return alt_return
            except:
                if catch: return catch(sys.exc_info(), lambda:func(*args,**kwargs))
                raise
        finally:
            if final: final()
    return _exceptional

def final(func,final=None,catch=None,alt_exceptions=(),alt_return=None):
    """connects a final call to a function call"""
    def _exceptional(*args,**kwargs):
        try:
            try: return func(*args,**kwargs)
            except alt_exceptions:
                return alt_return
            except:
                if catch: return catch(sys.exc_info(), lambda:func(*args,**kwargs))
                raise
        finally:
            if final: final()
    return _exceptional


def compose(func_1, func_2, unpack=False):
    """
    compose(func_1, func_2, unpack=False) -> function
    
    The function returned by compose is a composition of func_1 and func_2.
    That is, compose(func_1, func_2)(5) == func_1(func_2(5))
    """
    if not callable(func_1):
        raise TypeError("First argument to compose must be callable")
    if not callable(func_2):
        raise TypeError("Second argument to compose must be callable")
    
    if unpack:
        def composition(*args, **kwargs):
            return func_1(*func_2(*args, **kwargs))
    else:
        def composition(*args, **kwargs):
            return func_1(func_2(*args, **kwargs))
    return composition