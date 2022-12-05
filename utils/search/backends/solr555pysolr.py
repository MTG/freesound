# -*- coding: utf-8 -*-

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

from builtins import str
import json
import random
import re
import types
import math
from datetime import date, datetime

import pysolr
from django.conf import settings

from forum.models import Post
from sounds.models import Sound
from utils.text import remove_control_chars
from utils.search import SearchEngineBase, SearchResults
from utils.search.backends.solr451custom import SolrQuery, SolrResponseInterpreter


SOLR_FORUM_URL = settings.SOLR5_FORUM_URL
SOLR_SOUNDS_URL = settings.SOLR5_SOUNDS_URL


# Mapping from db sound field names to solr sound field names
FIELD_NAMES_MAP = {
    settings.SEARCH_SOUNDS_FIELD_ID: 'id',
    settings.SEARCH_SOUNDS_FIELD_NAME: 'original_filename',
    settings.SEARCH_SOUNDS_FIELD_TAGS: 'tag',
    settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 'description',
    settings.SEARCH_SOUNDS_FIELD_USER_NAME: 'username',
    settings.SEARCH_SOUNDS_FIELD_PACK_NAME: 'pack_tokenized',
    settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING: 'grouping_pack',
    settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: 'samplerate',
    settings.SEARCH_SOUNDS_FIELD_BITRATE: 'bitrate',
    settings.SEARCH_SOUNDS_FIELD_BITDEPTH: 'bitdepth',
    settings.SEARCH_SOUNDS_FIELD_TYPE: 'type',
    settings.SEARCH_SOUNDS_FIELD_CHANNELS: 'channels',
    settings.SEARCH_SOUNDS_FIELD_LICENSE_NAME: 'license'
}


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
    settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST: "avg_rating asc"
}


# Map of suffixes used for each type of dynamic fields defined in our Solr schema
# The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer),
# '*_s' (for string) and '*_ls' (for lists of strings)
SOLR_DYNAMIC_FIELDS_SUFFIX_MAP = {
    float: '_d',
    int: '_i',
    bool: '_b',
    str: '_s',
    list: '_ls',
}


SOLR_SOUND_FACET_DEFAULT_OPTIONS = {
    'limit': 5,
    'sort': True,
    'mincount': 1,
    'count_missing': False
}


def convert_sound_to_search_engine_document(sound):
    """
    TODO: Document that this includes remove_control_chars due to originally sending XML. not strictly necessary when submitting
          to json (and also, freesound model code fixes this), but keep it in to ensure that docs are clean.
    TODO: Assert that sound object is correct?
    """
    document = {}

    # Basic sound fields
    keep_fields = ['username', 'created', 'is_explicit', 'is_remix', 'num_ratings', 'channels', 'md5',
                   'was_remixed', 'original_filename', 'duration', 'id', 'num_downloads', 'filesize']
    for key in keep_fields:
        document[key] = getattr(sound, key)
    if sound.type == '':
        document["type"] = "wav"
    else:
        document["type"] = sound.type
    document["original_filename"] = remove_control_chars(getattr(sound, "original_filename"))
    document["description"] = remove_control_chars(getattr(sound, "description"))
    document["tag"] = getattr(sound, "tag_array")
    document["license"] = getattr(sound, "license_name")
    if document["num_ratings"] >= settings.MIN_NUMBER_RATINGS:
        document["avg_rating"] = getattr(sound, "avg_rating")
    else:
        document["avg_rating"] = 0

    if getattr(sound, "pack_id"):
        document["pack"] = remove_control_chars(getattr(sound, "pack_name"))
        document["grouping_pack"] = str(getattr(sound, "pack_id")) + "_" + remove_control_chars(
            getattr(sound, "pack_name"))
    else:
        document["grouping_pack"] = str(getattr(sound, "id"))

    document["is_geotagged"] = False
    if getattr(sound, "geotag_id"):
        document["is_geotagged"] = True
        if not math.isnan(getattr(sound, "geotag_lon")) and not math.isnan(getattr(sound, "geotag_lat")):
            document["geotag"] = str(getattr(sound, "geotag_lon")) + " " + str(getattr(sound, "geotag_lat"))

    document["bitdepth"] = getattr(sound, "bitdepth") if getattr(sound, "bitdepth") else 0
    document["bitrate"] = getattr(sound, "bitrate") if getattr(sound, "bitrate") else 0
    document["samplerate"] = int(getattr(sound, "samplerate")) if getattr(sound, "samplerate") else 0

    document["comment"] = [remove_control_chars(comment_text) for comment_text in getattr(sound, "comments_array")]
    document["comments"] = getattr(sound, "num_comments")
    locations = sound.locations()
    document["waveform_path_m"] = locations["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = locations["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = locations["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = locations["display"]["spectral"]["L"]["path"]
    document["preview_path"] = locations["preview"]["LQ"]["mp3"]["path"]

    # Analyzer's output
    for analyzer_name, analyzer_info in settings.ANALYZERS_CONFIGURATION.items():
        if 'descriptors_map' in analyzer_info:
            query_select_name = analyzer_name.replace('-', '_')
            analysis_data = getattr(sound, query_select_name, None)
            if analysis_data is not None:
                # If analysis is present, index all existing analysis fields using SOLR dynamic fields depending on
                # the value type (see SOLR_DYNAMIC_FIELDS_SUFFIX_MAP) so solr knows how to treat when filtering, etc.
                for key, value in analysis_data.items():
                    if type(value) == list:
                        # Make sure that the list is formed by strings
                        value = ['{}'.format(item) for item in value]
                    suffix = SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.get(type(value), None)
                    if suffix:
                        document['{0}{1}'.format(key, suffix)] = value
    return document


def convert_post_to_search_engine_document(post):
    body = remove_control_chars(post.body)
    if not body:
        return None

    document = {
        "id": post.id,
        "thread_id": post.thread.id,
        "thread_title": remove_control_chars(post.thread.title),
        "thread_author": post.thread.author.username,
        "thread_created": post.thread.created,

        "forum_name": post.thread.forum.name,
        "forum_name_slug": post.thread.forum.name_slug,

        "post_author": post.author.username,
        "post_created": post.created,
        "post_body": body,

        "num_posts": post.thread.num_posts,
        "has_posts": False if post.thread.num_posts == 0 else True
    }
    return document


def add_solr_suffix_to_dynamic_fieldname(fieldname):
    """Add the corresponding SOLR dynamic field suffix to the given fieldname. If the fieldname does not correspond
    to a dynamic field, leave it unchanged. See docstring in 'add_solr_suffix_to_dynamic_fieldnames_in_filter' for
    more information"""
    dynamic_fields_map = {}
    for analyzer, analyzer_data in settings.ANALYZERS_CONFIGURATION.items():
        if 'descriptors_map' in analyzer_data:
            descriptors_map = settings.ANALYZERS_CONFIGURATION[analyzer]['descriptors_map']
            for _, db_descriptor_key, descriptor_type in descriptors_map:
                dynamic_fields_map[db_descriptor_key] = '{}{}'.format(
                    db_descriptor_key, SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[descriptor_type])
    return dynamic_fields_map.get(fieldname, fieldname)



def add_solr_suffix_to_dynamic_fieldnames_in_filter(query_filter):
    """Processes a filter string containing field names and replaces the occurrences of fieldnames that match with
    descriptor names from the descriptors_map of different configured analyzers with updated fieldnames with
    the required SOLR dynamic field suffix. This is needed because fields from analyzers are indexed as dynamic
    fields which need to end with a specific suffi that SOLR uses to learn about the type of the field and how it
    should treat it.
    """
    for analyzer, analyzer_data in settings.ANALYZERS_CONFIGURATION.items():
        if 'descriptors_map' in analyzer_data:
            descriptors_map = settings.ANALYZERS_CONFIGURATION[analyzer]['descriptors_map']
            for _, db_descriptor_key, descriptor_type in descriptors_map:
                query_filter = query_filter.replace(
                    '{0}:'.format(db_descriptor_key),'{0}{1}:'.format(
                        db_descriptor_key, SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[descriptor_type]))
    return query_filter


def search_process_sort(sort):
    """Translates sorting criteria to solr sort criteria and add extra criteria if sorting by ratings.

    If order by rating, when rating is the same sort also by number of ratings.

    Args:
        sort (str): sorting criteria as defined in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB.

    Returns:
        List[str]: list containing the sorting field names list for the search engine.
    """
    if sort in [sort_web_name for sort_web_name, sort_field_name in SORT_OPTIONS_MAP.items()]:
        if sort == "avg_rating desc":
            sort = [SORT_OPTIONS_MAP[sort], "num_ratings desc"]
        elif sort == "avg_rating asc":
            sort = [SORT_OPTIONS_MAP[sort], "num_ratings asc"]
        else:
            sort = [SORT_OPTIONS_MAP[sort]]
    else:
        sort = [SORT_OPTIONS_MAP[settings.SEARCH_SOUNDS_SORT_DEFAULT]]
    return sort


def search_filter_make_intersection(query_filter):
    # In solr 4, fl="a:1 b:2" will take the AND of these two filters, but in solr 5+, this will use OR
    # fl=a:1&fl=b:2 can be used to take an OR, however we don't support this syntax
    # The AND behaviour can be approximated by using fl="+a:1 +b:2", however, fl="+a:1 OR +b:2" will still do an AND
    # In the Freesound API documentation, we document and support fl="a:(1 OR 2)" as a behaviour, but we
    # never documented fl="a:1 OR b:2" as a valid syntax, and looking at search logs we cannot see anyone using
    # this behaviour. Therefore, add a + to the beginning of each query item to force AND.
    # NOTE: for the filter names we match "a-zA-Z_" instead of using \w as using \w would cause problems for filters
    # which have date ranges inside.
    query_filter = re.sub(r'\b([a-zA-Z_]+:)', r'+\1', query_filter)
    return query_filter


def search_process_filter(query_filter, only_sounds_within_ids=False, only_sounds_with_pack=False):
    """Process the filter to make a number of adjustments

        1) Add type suffix to human-readable audio analyzer descriptor names (needed for dynamic solr field names).
        2) If only sounds with pack should be returned, add such a filter.
        3) Add filter for sound IDs if only_sounds_within_ids is passed.
        4) Rewrite geotag bounding box queries to use solr 5+ syntax

    Step 1) is used for the dynamic field names used in Solr (e.g. ac_tonality -> ac_tonality_s, ac_tempo ->
    ac_tempo_i). The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float),
    '*_i' (for integer) and '*_s' (for string). At indexing time, we append these suffixes to the analyzer
    descriptor names that need to be indexed so Solr can treat the types properly. Now we automatically append the
    suffices to the filter names so users do not need to deal with that and Solr understands recognizes the field name.

    Args:
        query_filter (str): query filter string.
        only_sounds_with_pack (bool, optional): whether to only include sounds that belong to a pack
        only_sounds_within_ids (List[int], optional): restrict search results to sounds with these IDs

    Returns:
        str: processed filter query string.
    """
    # Add type suffix to human-readable audio analyzer descriptor names which is needed for solr dynamic fields
    query_filter = add_solr_suffix_to_dynamic_fieldnames_in_filter(query_filter)

    # If we only want sounds with packs and there is no pack filter, add one
    if only_sounds_with_pack and not 'pack:' in query_filter:
        query_filter += ' pack:*'

    if 'geotag:"Intersects(' in query_filter:
        # Replace geotag:"Intersects(<MINIMUM_LONGITUDE> <MINIMUM_LATITUDE> <MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>)"
        #    with geotag:["<MINIMUM_LATITUDE>, <MINIMUM_LONGITUDE>" TO "<MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>"]
        query_filter = re.sub('geotag:"Intersects\((.+?) (.+?) (.+?) (.+?)\)"', r'geotag:["\2,\1" TO "\4,\3"]', query_filter)

    query_filter = search_filter_make_intersection(query_filter)

    # When calculating results form clustering, the "only_sounds_within_ids" argument is passed and we filter
    # our query to the sounds in that list of IDs.
    if only_sounds_within_ids:
        sounds_within_ids_filter = ' OR '.join(['id:{}'.format(sound_id) for sound_id in only_sounds_within_ids])
        if query_filter:
            query_filter += ' AND ({})'.format(sounds_within_ids_filter)
        else:
            query_filter = '({})'.format(sounds_within_ids_filter)

    return query_filter


class FreesoundSoundJsonEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        elif isinstance(value, date):
            return value.strftime('%Y-%m-%dT00:00:00.000Z')

        return json.JSONEncoder.default(self, value)

class SolrQueryPySolr(SolrQuery):

    def as_dict(self):
        params = {k: v for k, v in self.params.items() if v is not None}
        for k, v in params.items():
            if type(v) == bool:
                params[k] = json.dumps(v)
        return params

class Solr555PySolrSearchEngine(SearchEngineBase):
    sounds_index = None
    forum_index = None

    def get_sounds_index(self):
        if self.sounds_index is None:
            self.sounds_index = pysolr.Solr(
                SOLR_SOUNDS_URL,
                encoder=FreesoundSoundJsonEncoder(),
                results_cls=SolrResponseInterpreter,
                search_handler="fsquery",
                always_commit=True
            )
        return self.sounds_index

    def get_forum_index(self):
        if self.forum_index is None:
            self.forum_index = pysolr.Solr(
                SOLR_FORUM_URL,
                encoder=FreesoundSoundJsonEncoder(),
                results_cls=SolrResponseInterpreter,
                search_handler="fsquery",
                always_commit=True
            )
        return self.forum_index

    # Sound methods
    def add_sounds_to_index(self, sound_objects):
        documents = [convert_sound_to_search_engine_document(s) for s in sound_objects]
        self.get_sounds_index().add(documents)

    def remove_sounds_from_index(self, sound_objects_or_ids):
        for sound_object_or_id in sound_objects_or_ids:
            if type(sound_object_or_id) != Sound:
                sound_id = sound_object_or_id
            else:
                sound_id = sound_object_or_id.id
            self.get_sounds_index().delete(id=str(sound_id))

    def remove_all_sounds(self):
        """Removes all sounds from the search index"""
        self.get_sounds_index().delete(q="*:*")

    def sound_exists_in_index(self, sound_object_or_id):
        if type(sound_object_or_id) != Sound:
            sound_id = sound_object_or_id
        else:
            sound_id = sound_object_or_id.id
        response = self.search_sounds(query_filter='id:{}'.format(sound_id), offset=0, num_sounds=1)
        return response.num_found > 0

    def search_sounds(self, textual_query='', query_fields=None, query_filter='', offset=0, current_page=None,
                      num_sounds=settings.SOUNDS_PER_PAGE, sort=settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC,
                      group_by_pack=False, facets=None, only_sounds_with_pack=False, only_sounds_within_ids=False,
                      group_counts_as_one_in_facets=False):

        query = SolrQueryPySolr()


        # Process search fields: replace "db" field names by solr field names and set default weights if needed
        if query_fields is None:
            # If no fields provided, use the default
            query_fields = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS
        if type(query_fields) == list:
            query_fields = [add_solr_suffix_to_dynamic_fieldname(FIELD_NAMES_MAP.get(field, field)) for field in query_fields]
        elif type(query_fields) == dict:
            # Also remove fields with weight <= 0
            query_fields = [(add_solr_suffix_to_dynamic_fieldname(FIELD_NAMES_MAP.get(field, field)), weight)
                for field, weight in query_fields.items() if weight > 0]

        # Set main query options
        query.set_dismax_query(textual_query, query_fields=query_fields)

        # Process filter
        query_filter = search_process_filter(query_filter,
                                             only_sounds_within_ids=only_sounds_within_ids,
                                             only_sounds_with_pack=only_sounds_with_pack)

        # Set other query options
        if current_page is not None:
            offset = (current_page - 1) * num_sounds
        query.set_query_options(start=offset,
                                rows=num_sounds,
                                field_list=["id"],  # We only want the sound IDs of the results as we load data from DB
                                filter_query=query_filter,
                                sort=search_process_sort(sort))

        # Configure facets
        if facets is not None:
            facet_fields = [FIELD_NAMES_MAP[field_name] for field_name, _ in facets.items()]
            query.add_facet_fields(*facet_fields)
            query.set_facet_options_default(**SOLR_SOUND_FACET_DEFAULT_OPTIONS)
            for field_name, extra_options in facets.items():
                query.set_facet_options(FIELD_NAMES_MAP[field_name], **extra_options)

        # Configure grouping
        if group_by_pack:
            query.set_group_field(group_field="grouping_pack")
            query.set_group_options(
                group_func=None,
                group_query=None,
                group_rows=10,  # TODO: if limit is lower than rows and start=0, this should probably be equal to limit
                group_start=0,
                group_limit=1,  # This is the number of documents that will be returned for each group.
                group_offset=0,
                group_sort=None,
                group_sort_ingroup=None,
                group_format='grouped',
                group_main=False,
                group_num_groups=True,
                group_cache_percent=0,
                group_truncate=group_counts_as_one_in_facets)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter (the response from .search()).
        # We do it in this way to conform to SearchEngine.search_sounds definition which must return SearchResults
        results = self.get_sounds_index().search(**query.as_dict())
        return SearchResults(
            docs=results.docs,
            num_found=results.num_found,
            start=results.start,
            num_rows=results.num_rows,
            non_grouped_number_of_results=results.non_grouped_number_of_results,
            facets=results.facets,
            highlighting=results.highlighting,
            q_time=results.q_time
        )

    def get_random_sound_id(self):
        query = SolrQueryPySolr()
        rand_key = random.randint(1, 10000000)
        sort = ['random_%d asc' % rand_key]
        filter_query = 'is_explicit:0'
        query.set_query("*:*")
        query.set_query_options(start=0, rows=1, field_list=["id"], filter_query=filter_query, sort=sort)
        response = self.get_sounds_index().search(search_handler="select", **query.as_dict())
        docs = response.docs
        if docs:
            return int(docs[0]['id'])
        return 0

    # Forum posts methods
    def add_forum_posts_to_index(self, forum_post_objects):
        documents = [convert_post_to_search_engine_document(p) for p in forum_post_objects]
        documents = [d for d in documents if d is not None]
        self.get_forum_index().add(documents)

    def remove_forum_posts_from_index(self, forum_post_objects_or_ids):
        for post_object_or_id in forum_post_objects_or_ids:
            if type(post_object_or_id) != Post:
                post_id = post_object_or_id
            else:
                post_id = post_object_or_id.id
            self.get_forum_index().delete(id=str(post_id))

    def remove_all_forum_posts(self):
        """Removes all forum posts from the search index"""
        self.get_forum_index().delete(q="*:*")

    def forum_post_exists_in_index(self, forum_post_object_or_id):
        if type(forum_post_object_or_id) != Post:
            post_id = forum_post_object_or_id
        else:
            post_id = forum_post_object_or_id.id
        response = self.search_forum_posts(query_filter='id:{}'.format(post_id), offset=0, num_posts=1)
        return response.num_found > 0

    def search_forum_posts(self, textual_query='', query_filter='', offset=0, current_page=None,
                           num_posts=settings.FORUM_POSTS_PER_PAGE, group_by_thread=True):
        query = SolrQueryPySolr()
        query.set_dismax_query(textual_query, query_fields=[("thread_title", 4),
                                                            ("post_body", 3),
                                                            ("thread_author", 3),
                                                            ("post_author", 3),
                                                            ("forum_name", 2)])
        query.set_highlighting_options_default(field_list=["post_body"],
                                               fragment_size=200,
                                               alternate_field="post_body",
                                               require_field_match=False,
                                               pre="<strong>",
                                               post="</strong>")
        if current_page is not None:
            offset = (current_page - 1) * num_posts
        query.set_query_options(start=offset,
                                rows=num_posts,
                                field_list=["id",
                                            "forum_name",
                                            "forum_name_slug",
                                            "thread_id",
                                            "thread_title",
                                            "thread_author",
                                            "thread_created",
                                            "post_body",
                                            "post_author",
                                            "post_created",
                                            "num_posts"],
                                filter_query=query_filter,
                                sort=["thread_created desc"])

        if group_by_thread:
            query.set_group_field("thread_title_grouped")
            query.set_group_options(group_limit=30)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter (the response from .search()).
        # We do it in this way to conform to SearchEngine.search_sounds definition which must return SearchResults
        results = self.get_forum_index().search(**query.as_dict())
        return SearchResults(
            docs=results.docs,
            num_found=results.num_found,
            start=results.start,
            num_rows=results.num_rows,
            non_grouped_number_of_results=results.non_grouped_number_of_results,
            facets=results.facets,
            highlighting=results.highlighting,
            q_time=results.q_time
        )

    # Tag clouds methods
    def get_user_tags(self, username):
        query = SolrQueryPySolr()
        query.set_dismax_query('*:*')
        filter_query = 'username:\"%s\"' % username
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=10, mincount=1)
        results = self.get_sounds_index().search(search_handler="select", **query.as_dict())
        return results.facets['tag']

    def get_pack_tags(self, username, pack_name):
        query = SolrQueryPySolr()
        query.set_dismax_query('*:*')
        filter_query = 'username:\"%s\" pack:\"%s\"' % (username, pack_name)
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=20, mincount=1)
        results = self.get_sounds_index().search(search_handler="select", **query.as_dict())
        return results.facets['tag']
