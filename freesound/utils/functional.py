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