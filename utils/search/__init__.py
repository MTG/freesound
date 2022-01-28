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

from django.conf import settings


SERACH_INDEX_SOUNDS = 'search_index_sounds'
SERACH_INDEX_FORUM = 'search_index_forum'


class SearchResults(object):

    def __init__(self, docs=None, num_found=-1, start=-1, num_rows=-1, non_grouped_number_of_results=-1,
                 facets=None, highlighting=None, q_time=-1):
        """
        Class that holds the results of a search query. It must contain the fields defined below.

        Args:
            docs (List[Dict]): list of dictionaries with the results of the query. Each dict object includes information
                about that individual result. That information is typically the ID of the matched object (Eg: the ID
                of a sound), but it can also include other properties. Here is a list of possible properties:
                - id (int): ID of the matched object (a sound or forum post). If results are grouped, this will be the ID of
                    the first matching result in the group
                - group_name (str): the name of the group. This includes the value of the grouping field shared by all
                    grouped results (only if grouping).
                - group_docs (List[Dict]): information about of results in the group. This is a list of dictionaries
                    with the data fields of the matched results (see examples below).  It can be that not all results
                    from the group are in this list (for example when grouping sounds by pack, we only want the first
                    sound result of the pack).
                - n_more_in_group (int): number of other matching results in the same group of the result (only
                    when grouping results). This number can be larger than the length of "group_docs" if the query
                    was configured to only return a limited number of results per group.
                Here is an example with IDs as the only property returned for each result:
                    docs = [{'id': 410650}, {'id': 412456}, {'id': 411506}, {'id': 411508}, {'id': 412404}, ...]
                Another example with extra properties returned for each result:
                    docs = [{
                        'id': 91368,
                        'post_body': 'Firstly, just want to say I absolutely love that...',
                        'thread_author': 'frederic.font',
                        'forum_name': 'Freesound Project',
                        'forum_name_slug': 'freesound-project'
                    }, {
                        'id': 143,
                        'post_body': 'testBody',
                        'thread_author': 'testuser',
                        'forum_name': 'testForum',
                        'forum_name_slug': 'test_forum'
                    }, ... ]
                Another example for a sounds query with results grouped by pack:
                    docs = [
                        {'group_name': '410477', 'group_docs': [{'id': 410477}], 'id': 410477, 'n_more_in_group': 0},
                        {'group_name': '22732_Make Noise Crew Reels', 'group_docs': [{'id': 407441}], 'id': 407441, 'n_more_in_group': 9},
                        {'group_name': '23378_Dirty Loopz', 'group_docs': [{'id': 414752}], 'id': 414752, 'n_more_in_group': 5},
                        ...
                    ]
                And another example for a forum posts query without grouping results:
                    docs = [{
                        'id': 91368,
                        'n_more_in_group': 23,
                        'group_name': 'testThread,
                        'group_docs': [{
                            'id': 91368,
                            'post_body': 'Firstly, just want to say I absolutely love that...',
                            'thread_author': 'frederic.font',
                            'forum_name': 'Freesound Project',
                            'forum_name_slug': 'freesound-project'
                        }, {
                            'id': 143
                            'post_body': 'testBody',
                            'thread_author': 'testuser',
                            'forum_name': 'testForum',
                            'forum_name_slug': 'test_forum'
                        }, ... ]
                    }, ...]
            start (int): offset of the search results query (Eg: return matched documents starting at 15)
            num_rows (int): number of results per "page"
            num_found (int): total number of matches found
            non_grouped_number_of_results (int, optional):  total number of non-grouped matches found (it will be
                the same as num_found for queries which did not group results)
            facets (Dict{str:List[Tuple(str,int)]}, optional): data structure including information about the facets
                calculated by the search engine. The keys of the main dictionary correspond to the field names of each
                returned facet. For each facet, a list of tuples is returned with the most common facet elements and
                their count (sorted in descending count order). Ecample:
                    facets = {
                        'username': [('wjoojoo', 64), ('zbylut', 58), ('filipefalcao', 52), ('lonemonk', 49), ...]
                        'bitdepth': [('16', 938), ('24', 594), ('0', 298), ('32', 68), ('4', 4)],
                        'license': [('Attribution', 890), ('Creative Commons 0', 727), ...]
                     }
            highlighting (Dict{str:Dict}): datab structure containing "highlighted" contents of the search results (if
                any). This could be the content of a forum post with the words that matched the search criteria
                surrounded by "<strong></strong>" tags.

                highlighting = {
                    '71523': {'post_body': ["You are going to be our <strong>test</strong> subject.\nQ)-Don't..."]},
                    '133': {'post_body': ["post with no"]},
                    '31943': {'post_body': [" the level by 4db.  In broadcasting 0db is the pivotal..."]
                }

            q_time (int, optional): time that it took to execute the query in the backend, in ms
        """
        self.docs = docs if docs is not None else list()
        self.facets = facets if facets is not None else list()
        self.highlighting = highlighting if highlighting is not None else list()
        self.non_grouped_number_of_results = non_grouped_number_of_results
        self.num_found = num_found
        self.start = start
        self.num_rows = num_rows
        self.q_time = q_time

    def __str__(self):
        return '<SearchResults with {} results found>'.format(self.num_found)


class SearchResultsPaginator(object):

    def __init__(self, search_results, num_per_page):
        """Paginator object for search results which has a similar API to django.core.paginator.Paginator

        Note that the results of a query are already paginated. This paginator is a simple wrapper to provide a
        pagination API for search results similar to that of the official django.core.paginator.Paginator

        Args:
            search_results (SearchResults): results of a query
            num_per_page: number of results per page
        """
        self.num_per_page = num_per_page
        self.results = search_results.docs
        self.count = search_results.num_found
        self.num_pages = search_results.num_found / num_per_page + int(search_results.num_found % num_per_page != 0)
        self.page_range = range(1, self.num_pages + 1)

    def page(self, page_num):
        has_next = page_num < self.num_pages
        has_previous = 1 < page_num <= self.num_pages
        return {
            'object_list': self.results,
            'has_next': has_next,
            'has_previous': has_previous,
            'has_other_pages': has_next or has_previous,
            'next_page_number': page_num + 1,
            'previous_page_number': page_num - 1
        }


class SearchEngineException(Exception):
    pass


class SearchEngineBase(object):

    index_name = None

    def __init__(self, index_name):
        self.index_name = index_name

    # Many of the methods here should probably be removed from main SearchEngine API as the endpoints are only
    # application-specific

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

    # Sound search related methods

    def convert_sound_to_search_engine_document(self, sound):
        raise NotImplementedError

    def add_sounds_to_index(self, sounds):
        if self.index_name != SERACH_INDEX_SOUNDS:
            raise SearchEngineException("Trying to add sounds to non-sounds index")
        documents = [self.convert_sound_to_search_engine_document(s) for s in sounds]
        self.add_to_index(documents)

    def search_sounds(self, textual_query='', query_fields=None, query_filter='', offset=0, current_page=None,
                      num_sounds=10, sort=settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC, group_by_pack=False,
                      facets=None, only_sounds_with_pack=False, only_sounds_within_ids=False,
                      group_counts_as_one_in_facets=False):
        """Search for sounds that match specific criteria and return them in a SearchResults object

        Args:
            textual_query (str, optional): the textual query
            query_fields (List[str] or Dict{str: int}, optional): a list of the fields that should be matched when
            querying. Field weights can also be specified if a dict is passed with keys as field names and values as
            weights. Field names should use the names defined in settings.SEARCH_SOUNDS_FIELD_*. Eg:
                query_fields = [settings.SEARCH_SOUNDS_FIELD_ID, settings.SEARCH_SOUNDS_FIELD_USER_NAME]
                query_fields = {settings.SEARCH_SOUNDS_FIELD_ID:1 , settings.SEARCH_SOUNDS_FIELD_USER_NAME: 4}
            query_filter (str, optional): filter expression following lucene filter syntax
            offset (int, optional): offset for the returned results
            current_page (int, optional): alternative way to set offset using page numbers. Using current_page will
                set offset like offset=current_page*num_sounds
            num_sounds (int, optional): number of sounds to return
            sort (str, optional): sorting criteria. should be one of settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB
            group_by_pack (bool, optional): whether the search results should be grouped by sound pack. When grouped
                by pack, only 1 sound per pack will be returned, together with additional information about the number
                of other sounds in the pack that would be i the same group.
            facets (Dict{str: Dict}, optional): information about facets to be returned. Can be None if no faceting
                information is required. Facets should be specified as a dictionary with the "db" field names to be
                included in the faceting as keys, and a dictionary as values with optional specific parameters for
                every field facet. Field names should use the names defined in settings.SEARCH_SOUNDS_FIELD_*. Eg:
                    {
                        settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: {},
                        settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING: {'limit': 10},
                        settings.SEARCH_SOUNDS_FIELD_USER_NAME: {'limit': 30}
                    }
                Supported individual facet options include:
                    - limit: the number of items returned per facet
            only_sounds_with_pack (bool, optional): whether to only include sounds that belong to a pack
            only_sounds_within_ids (List[int], optional): restrict search results to sounds with these IDs
            group_counts_as_one_in_facets (bool, optional): whether only one result from a group should be counted
                when computing facets or all should be taken into account. This is used to reduce the influence of
                large groups in facets. We use it for computing the main tag cloud and avoiding a large packs of sounds
                with the same tags to largely influence the general tag cloud (only one sound of the pack will be
                counted)

        Returns:
            SearchResults: SearchResults object containing the results of the query
        """
        raise NotImplementedError

    def get_random_sound_id(self):
        """Return the id of a random sound from the search engine.
        This is used for random sound browsing. We filter explicit sounds,
        but otherwise don't have any other restrictions on sound attributes.

        Returns:
            int: the ID of the selected random sound (or 0 if there were errors)
        """
        raise NotImplementedError

    def sound_exists_in_index(self, sound):
        """Check if a sound is indexed in the search engine

        Args:
            sound (sounds.models.Sound): Sound object to check if indexed

        Returns:
            bool: whether the sound is indexed in the search engine
        """
        raise NotImplementedError

    # Forum search related methods

    def convert_post_to_search_engine_document(self, post):
        raise NotImplementedError

    def add_forum_posts_to_index(self, forum_posts):
        if self.index_name != SERACH_INDEX_FORUM:
            raise SearchEngineException("Trying to add forum posts to non-posts index")
        documents = [self.convert_post_to_search_engine_document(p) for p in forum_posts]        
        self.add_to_index(documents)

    def search_posts(self):
        raise NotImplementedError


    # Other "application" methods

    def get_user_tags(self, username):
        """Retrieves the tags used by a user and their counts

        Args:
            username: name of the user for which we want to know tags and counts

        Returns:
            List[Tuple(str, int)]: List of tuples with the tags and counts of the tags used by the user.
                Eg: [('cat', 1), ('echo', 1), ('forest', 1)]
        """
        raise NotImplementedError

    def get_pack_tags(self, username, pack_name):
        """Retrieves the tags in the sounds of a pack and their counts

        Args:
            username: name of the user who owns the pack
            pack_name: name of the pack for which tags and counts should be retrieved

        Returns:
            List[Tuple(str, int)]: List of tuples with the tags and counts of the tags in the pack.
                Eg: [('cat', 1), ('echo', 1), ('forest', 1)]
        """
        raise NotImplementedError


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
