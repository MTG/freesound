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

import math
from django.conf import settings

SOLR_SOUND_FACET_DEFAULT_OPTIONS = {"limit": 5, "type": "terms", "sort": "count desc", "mincount": 1, "missing": False}

SOLR_DOC_CONTENT_TYPES = {"sound": "s", "similarity_vector": "v"}

# Mapping from db sound field names to solr sound field names
FIELD_NAMES_MAP = {
    settings.SEARCH_SOUNDS_FIELD_ID: "id",
    settings.SEARCH_SOUNDS_FIELD_NAME: "original_filename",
    settings.SEARCH_SOUNDS_FIELD_TAGS: "tag",
    settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: "description",
    settings.SEARCH_SOUNDS_FIELD_USER_NAME: "username",
    settings.SEARCH_SOUNDS_FIELD_PACK_NAME: "pack_tokenized",
    settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING: "grouping_pack",
    settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: "samplerate",
    settings.SEARCH_SOUNDS_FIELD_BITRATE: "bitrate",
    settings.SEARCH_SOUNDS_FIELD_BITDEPTH: "bitdepth",
    settings.SEARCH_SOUNDS_FIELD_TYPE: "type",
    settings.SEARCH_SOUNDS_FIELD_CHANNELS: "channels",
    settings.SEARCH_SOUNDS_FIELD_LICENSE_NAME: "license",
}

REVERSE_FIELD_NAMES_MAP = {value: key for key, value in FIELD_NAMES_MAP.items()}


# Map "web" sorting options to solr sorting options
SORT_OPTIONS_MAP = {
    settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC: "score desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST: "duration desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST: "duration asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST: "created desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST: "created asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST: "num_downloads desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST: "num_downloads asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST: "avg_rating desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST: "avg_rating asc",
}
SORT_OPTIONS_MAP_FORUM = {
    settings.SEARCH_FORUM_SORT_OPTION_THREAD_DATE_FIRST: "thread_created desc",
    settings.SEARCH_FORUM_SORT_OPTION_DATE_NEW_FIRST: "post_created desc",
}

# Map of suffixes used for each type of dynamic fields defined in our Solr schema
# The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer),
# '*_s' (for string) and '*_ls' (for lists of strings)
SOLR_DYNAMIC_FIELDS_SUFFIX_MAP = {
    float: "_d",
    int: "_i",
    bool: "_b",
    str: "_s",
    list: "_ls",
}


SOLR_VECTOR_FIELDS_DIMENSIONS_MAP = {
    100: "sim_vector100",
    512: "sim_vector512",
}


def get_search_engine(backend_class=settings.SEARCH_ENGINE_BACKEND_CLASS, sounds_index_url=None, forum_index_url=None):
    """Return SearchEngine class instance to carry out search engine actions

    Args:
        backend_class: path to the search engine backend class (defaults to settings.SEARCH_ENGINE_BACKEND_CLASS)
        sounds_index_url: url of the sounds index in solr. If not set, use the default URL for the backend
        forum_index_url: url of the forum index in solr. If not set, use the default URL for the backend

    Returns:
        utils.search.SearchEngineBase: search engine backend class instance
    """
    module_name, class_name = backend_class.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)(sounds_index_url, forum_index_url)


def get_solr_dense_vector_search_field_name(dimensions, l2_norm=False):
    base_field_name = SOLR_VECTOR_FIELDS_DIMENSIONS_MAP.get(dimensions, None)
    if base_field_name is None:
        return None
    if l2_norm:
        return f"{base_field_name}_l2"
    return base_field_name


class SearchResults:
    def __init__(
        self,
        docs=None,
        num_found=-1,
        start=-1,
        num_rows=-1,
        non_grouped_number_of_results=-1,
        facets=None,
        highlighting=None,
        q_time=-1,
    ):
        """
        Class that holds the results of a search query. It must contain the fields defined below.

        Args:
            docs (List[Dict]): list of dictionaries with the results of the query. Each dict object includes information
                about that individual result. That information is typically the ID of the matched object (Eg: the ID
                of a sound), but it can also include other properties. Here is a list of possible properties:
                - id (int): ID of the matched object (a sound or forum post). If results are grouped, this will be the ID of
                    the first matching result in the group
                - score (float): score of the matched object as provided by the search engine
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
        self.facets = facets if facets is not None else dict()
        self.highlighting = highlighting if highlighting is not None else dict()
        self.non_grouped_number_of_results = non_grouped_number_of_results
        self.num_found = num_found
        self.start = start
        self.num_rows = num_rows
        self.q_time = q_time

    def __str__(self):
        return f"<SearchResults with {self.num_found} results found>"


class SearchResultsPaginator:
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
        self.num_pages = math.ceil(search_results.num_found / num_per_page)
        self.page_range = list(range(1, self.num_pages + 1))

    def page(self, page_num):
        has_next = page_num < self.num_pages
        has_previous = 1 < page_num <= self.num_pages
        return {
            "object_list": self.results,
            "has_next": has_next,
            "has_previous": has_previous,
            "has_other_pages": has_next or has_previous,
            "next_page_number": page_num + 1,
            "previous_page_number": page_num - 1,
        }


class SearchEngineException(Exception):
    pass
