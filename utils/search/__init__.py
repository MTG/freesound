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


def get_search_engine(
    backend_class=settings.SEARCH_ENGINE_BACKEND_CLASS, sounds_index_url=None, forum_index_url=None
) -> "SearchEngineBase":
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
                their count (sorted in descending count order). Example:
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


class SearchEngineBase:
    solr_base_url = None

    # Test SearchEngineBase with `pytest -m "search_engine" utils/search/backends/test_search_engine_backend.py`

    # Sound search related methods

    def add_sounds_to_index(self, sound_objects, update=False, include_similarity_vectors=False):
        """Indexes the provided sound objects in the search index

        Args:
            sound_objects (list[sounds.models.Sound]): Sound objects of the sounds to index
            update (bool): Whether to perform an update of the existing documents in the index or to
                completely replace them. An update is useful so that fields not included in the document are
                not removed from the index.
            include_similarity_vectors (bool): Whether to include similarity vectors in the index.
        """
        raise NotImplementedError

    def update_similarity_vectors_in_index(self, sound_objects):
        """Create an update document to add only similarity vectors to sounds that already exist in the index"""
        raise NotImplementedError

    def remove_sounds_from_index(self, sound_objects_or_ids):
        """Removes sounds from the search index

        Args:
            sound_objects_or_ids (list[sounds.models.Sound] or list[int]):  Sound objects or sound IDs to remove
        """
        raise NotImplementedError

    def remove_all_sounds(self):
        """Removes all sounds from the search index"""
        raise NotImplementedError

    def sound_exists_in_index(self, sound_object_or_id):
        """Check if a sound is indexed in the search engine

        Args:
            sound_object_or_id (sounds.models.Sound or int): Sound object or sound ID to check if indexed

        Returns:
            bool: whether the sound is indexed in the search engine
        """
        raise NotImplementedError

    def get_all_sound_ids_from_index(self):
        """Return a list of all sound IDs indexed in the search engine

        Returns:
            List[int]: list of all sound IDs indexed in the search engine
        """
        raise NotImplementedError

    def search_sounds(
        self,
        textual_query="",
        query_fields=None,
        query_filter="",
        field_list=["id", "score"],
        offset=0,
        current_page=None,
        num_sounds=settings.SOUNDS_PER_PAGE,
        sort=settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC,
        group_by_pack=False,
        num_sounds_per_pack_group=1,
        facets=None,
        only_sounds_with_pack=False,
        only_sounds_within_ids=False,
        group_counts_as_one_in_facets=False,
        similar_to=None,
        similar_to_min_similarity=settings.SIMILARITY_MIN_THRESHOLD,
        similar_to_similarity_space=settings.SIMILARITY_SPACE_DEFAULT,
    ):
        """Search for sounds that match specific criteria and return them in a SearchResults object

        Args:
            textual_query (str, optional): the textual query
            query_fields (List[str] or Dict{str: int}, optional): a list of the fields that should be matched when
                querying. Field weights can also be specified if a dict is passed with keys as field names and values as
                weights. Field names should use the names defined in settings.SEARCH_SOUNDS_FIELD_*. Eg:
                    query_fields = [settings.SEARCH_SOUNDS_FIELD_ID, settings.SEARCH_SOUNDS_FIELD_USER_NAME]
                    query_fields = {settings.SEARCH_SOUNDS_FIELD_ID:1 , settings.SEARCH_SOUNDS_FIELD_USER_NAME: 4}
            query_filter (str, optional): filter expression following lucene filter syntax
            field_list (List[str], optional): list of fields to return by the search engine. Typically we're only interested
                in sound IDs because we don't use data form the search engine to display sounds, but in some cases it can
                be necessary to return further data.
            offset (int, optional): offset for the returned results
            current_page (int, optional): alternative way to set offset using page numbers. Using current_page will
                set offset like offset=current_page*num_sounds
            num_sounds (int, optional): number of sounds to return
            sort (str, optional): sorting criteria. should be one of settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB
            group_by_pack (bool, optional): whether the search results should be grouped by sound pack. When grouped
                by pack, only "num_sounds_per_pack_group" sounds per pack will be returned, together with additional
                information about the number of other sounds in the pack that would be i the same group.
            num_sounds_per_pack_group (int, optional): number of sounds to return per pack group (minimum one)
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
            similar_to (int or List[float], optional): sound ID or similarity vector to be used as target for similarity
                search. Note that when this parameter is passed, some of the other parameters will be ignored
                ('textual_query', 'facets', 'group_by_pack', 'num_sounds_per_pack_group', 'group_counts_as_one_in_facets').
                'query_filter' should still be usable, although this remains to be thoroughly tested.
            similar_to_min_similarity (float, optional): min similarity score to consider a sound as similar.
            similar_to_similarity_space (str, optional): similarity space from which to select similarity vectors for
                similarity search. It defaults to settings.SIMILARITY_SPACE_DEFAULT, but it can be changed to something
                else if we want to use a different type of similarity vectors for a similarity search query.

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

    def get_num_sim_vectors_indexed_per_similarity_space(self):
        """Returns the number of similarity vectors indexed in the search engine for each
        similarity space. Because there might be several similarity vectors per sound, we distinguish
        between the total number of similarity vectors and the total number of sounds per similarity space.

        Returns:
            dict: dictionary with the number of similarity vectors and number of sounds indexed per similarity space.
                E.g.: {'freesound_classic': {'num_sounds': 0, 'num_vectors': 0},
                       'laion_clap': {'num_sounds': 15876, 'num_vectors': 25448}}
        """
        raise NotImplementedError

    def get_all_sim_vector_document_ids_per_similarity_space(self):
        """Returns indexed Solr document IDs for all similarity vector documents for each similarity space.
        Solr document IDs for similarity vector documents have the format:
            "simvec_<similarity_space>_<sound_id>"

        Returns:
            dict: dictionary with a list of Solr document IDs per similarity space.
                E.g.: {'freesound_classic': [693610/similarity_vectors#0, 693610/similarity_vectors#1, ...],
                       'laion_clap': [1234/similarity_vectors#0, 1235/similarity_vectors#0, ...]}
        """
        raise NotImplementedError

    # Forum search related methods

    def add_forum_posts_to_index(self, forum_post_objects):
        """Indexes the provided forum post objects in the search index

        Args:
            forum_post_objects (list[forum.models.Post]): Post objects of the forum posts to index
        """
        raise NotImplementedError

    def remove_forum_posts_from_index(self, forum_post_objects_or_ids):
        """Removes forum posts from the search index

        Args:
            forum_post_objects_or_ids (list[forum.models.Post] or list[int]):  Post objects or post IDs to remove
        """
        raise NotImplementedError

    def remove_all_forum_posts(self):
        """Removes all forum posts from the search index"""
        raise NotImplementedError

    def forum_post_exists_in_index(self, forum_post_object_or_id):
        """Check if a sound is indexed in the search engine

        Args:
            forum_post_object_or_id (forum.models.Post or int): Post object or post ID to check if indexed

        Returns:
            bool: whether the post is indexed in the search engine
        """
        raise NotImplementedError

    def search_forum_posts(
        self,
        textual_query="",
        query_filter="",
        offset=0,
        sort=None,
        current_page=None,
        num_posts=settings.FORUM_POSTS_PER_PAGE,
        group_by_thread=True,
    ):
        """Search for forum posts that match specific criteria and return them in a SearchResults object

        Args:
            textual_query (str, optional): the textual query
            query_filter (str, optional): filter expression following lucene filter syntax
            offset (int, optional): offset for the returned results
            sort (str, optional): sorting criteria. should be one of settings.SEARCH_FORUM_SORT_OPTIONS_WEB
            current_page (int, optional): alternative way to set offset using page numbers. Using current_page will
                set offset like offset=current_page*num_sounds
            num_posts (int, optional): number of forum posts to return
            group_by_thread (bool, optional): whether the search results should be grouped by forum post thread. When
                grouped by thread, all matching results per every thread will be returned following the structure
                defined in SearchResults. Note that this is different than the group_by_pack option of search_sounds,
                with which only 1 result is returned per group.

        Returns:
            SearchResults: SearchResults object containing the results of the query

        """
        raise NotImplementedError

    # Tag clouds methods

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
