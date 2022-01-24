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

import importlib
import itertools
import logging

from django.conf import settings


SERACH_INDEX_SOUNDS = 'search_index_sounds'
SERACH_INDEX_FORUM = 'search_index_forum'


class SearchEngineException(Exception):
    pass


class SearchEngineBase(object):

    index_name = None

    def __init__(self, index_name):
        self.index_name = index_name

    def search(self, query):
        raise NotImplementedError
    
    def return_paginator(self, results, num_per_page):
        raise NotImplementedError

    def add_to_index(self, docs):
        raise NotImplementedError

    def remove_from_index(self, document_id):
        raise NotImplementedError

    def remove_from_index_by_query(self, query):
        raise NotImplementedError

    def remove_from_index_by_ids(self, document_ids):
        raise NotImplementedError

    def get_query_manager(self):
        raise NotImplementedError

    def convert_sound_to_search_engine_document(self, sound):
        raise NotImplementedError

    def convert_post_to_search_engine_document(self, post):
        raise NotImplementedError

    def add_sounds_to_index(self, sounds):
        if self.index_name != SERACH_INDEX_SOUNDS:
            raise SearchEngineException("Trying to add sounds to non-sounds index")
        documents = [self.convert_sound_to_search_engine_document(s) for s in sounds]
        self.add_to_index(documents)

    def add_forum_posts_to_index(self, forum_posts):
        if self.index_name != SERACH_INDEX_FORUM:
            raise SearchEngineException("Trying to add forum posts to non-posts index")
        documents = [self.convert_post_to_search_engine_document(p) for p in forum_posts]        
        self.add_to_index(documents)


class Multidict(dict):
    """A dictionary that represents a query string. If values in the dics are tuples, they are expanded.
    None values are skipped and all values are utf-encoded. We need this because in solr, we can have multiple
    fields with the same value, like facet.field

    >>> [ (key, value) for (key,value) in Multidict({"a": 1, "b": (2,3,4), "c":None, "d":False}).items() ]
    [('a', 1), ('b', 2), ('b', 3), ('b', 4), ('d', 'false')]
    """
    def items(self):
        # generator that retuns all items
        def all_items():
            for (key, value) in dict.items(self):
                if isinstance(value, tuple) or isinstance(value, list):
                    for v in value:
                        yield key, v
                else:
                    yield key, value

        # generator that filters all items: drop (key, value) pairs with value=None and convert bools to lower case strings
        for (key, value) in itertools.ifilter(lambda (key,value): value != None and value != "", all_items()):
            if isinstance(value, bool):
                value = unicode(value).lower()
            else:
                value = unicode(value).encode('utf-8')

            yield (key, value)


def get_search_engine():
    module_name, class_name = settings.SEARCH_ENGINE_BACKEND_CLASS.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)(index_name=SERACH_INDEX_SOUNDS)


def get_search_engine_forum():
    module_name, class_name = settings.SEARCH_ENGINE_BACKEND_CLASS.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)(index_name=SERACH_INDEX_FORUM)
