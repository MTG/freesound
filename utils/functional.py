#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import sys

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

def first(predicate, itterator):
    for item in itterator:
        if predicate(item):
            return item

def combine_dicts(dict1, dict2):
    return dict(dict1.items() + dict2.items())