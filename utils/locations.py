def locations_decorator(cache=True):
    """wraps a locations function and adds two things:
        * caching for the calculation done inside the function if cache is true
        * if the locations function is called with a string, do lookup like in django templates
            i.e. let's say locations() returns {"a": {"b": {"c" : 5}}}, calling
                locations()["a"]["b"]["c"]
            will result in the same as calling:
                locations("a.b.c")
            but is much easier on the typing and easier for copy-pasting
    """
    def decorator(locations_function):
        def wrapped(self, path=None):
            # cache the call to the locations function so it's only calculated once
            if not cache or not hasattr(self, '_locations_cache'):
                self._locations_cache = locations_function(self)
    
            if path:
                lookup = self._locations_cache
                for piece in path.split("."):
                    lookup = lookup[piece]
                return lookup
            else:
                return self._locations_cache
        return wrapped
    return decorator

def pretty_print_locations(locations, indent=0):
    for (key, value) in locations.iteritems():
        if isinstance(value, dict):
            print "  "*indent, "*", key
            pretty_print_locations(value, indent+1)
        else:
            print "  "*indent, "*", key


if __name__ == "__main__":
    class X(object):
        @locations_decorator()
        def locations(self):
            return dict(a=5)
    x = X()
    print x.locations()
    print x.locations()