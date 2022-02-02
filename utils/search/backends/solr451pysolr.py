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

import json
import random
import types
from datetime import date, datetime

import pysolr
from django.conf import settings

from forum.models import Post
from sounds.models import Sound
from utils.search import SearchEngineBase, SearchResults
from utils.search.backends.solr451custom import FIELD_NAMES_MAP, SOLR_FORUM_URL, SOLR_SOUNDS_URL, \
    SOLR_SOUND_FACET_DEFAULT_OPTIONS, convert_sound_to_search_engine_document, convert_post_to_search_engine_document, \
    search_process_filter, search_process_sort, SolrQuery, SolrResponseInterpreter


class SolrQueryPySolr(SolrQuery):

    def as_dict(self):
        params = {k: v for k, v in self.params.iteritems() if v is not None}
        for k, v in params.iteritems():
            if type(v) == types.BooleanType:
                params[k] = json.dumps(v)
        return params


def encode_value(value):
    if isinstance(value, datetime):
        value = value.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    elif isinstance(value, date):
        value = value.strftime('%Y-%m-%dT00:00:00.000Z')
    elif isinstance(value, bool):
        if value:
            value = 'true'
        else:
            value = 'false'
    else:
        value = unicode(value)
    return value


def encode_list_dicts(list_dicts):
    return [dict((k, encode_value(v)) for (k, v) in d.items()) for d in list_dicts]


class Solr451PySolrSearchEngine(SearchEngineBase):
    sounds_index = None
    forum_index = None

    def get_sounds_index(self):
        if self.sounds_index is None:
            self.sounds_index = pysolr.Solr(SOLR_SOUNDS_URL)
        return self.sounds_index

    def get_forum_index(self):
        if self.forum_index is None:
            self.forum_index =  pysolr.Solr(SOLR_FORUM_URL)
        return self.forum_index


    # Sound methods

    def add_sounds_to_index(self, sound_objects):
        documents = [convert_sound_to_search_engine_document(s) for s in sound_objects]
        self.get_sounds_index().add(encode_list_dicts(documents))
        self.get_sounds_index().commit()

    def remove_sounds_from_index(self, sound_objects_or_ids):
        for sound_object_or_id in sound_objects_or_ids:
            if type(sound_object_or_id) != Sound:
                sound_id = sound_object_or_id
            else:
                sound_id = sound_object_or_id.id
            self.get_sounds_index().delete(id=sound_id)
        self.get_sounds_index().commit()

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
            query_fields = [FIELD_NAMES_MAP[field] for field in query_fields]
        elif type(query_fields) == dict:
            # Also remove fields with weight <= 0
            query_fields = [(FIELD_NAMES_MAP[field], weight) for field, weight in query_fields.items() if weight > 0]

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
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter. This would not be strictly
        # needed because SearchResults and SolrResponseInterpreter are virtually the same, but we do it in this way to
        # conform to SearchEngine.search_sounds definition which must return SearchResults
        results = SolrResponseInterpreter(self.get_sounds_index().search(**query.as_dict()).raw_response)
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
        response = SolrResponseInterpreter(self.get_sounds_index().search(**query.as_dict()).raw_response)
        docs = response.docs
        if docs:
            return int(docs[0]['id'])
        return 0

    # Forum posts methods

    def add_forum_posts_to_index(self, forum_post_objects):
        documents = [convert_post_to_search_engine_document(p) for p in forum_post_objects]
        self.get_forum_index().add(encode_list_dicts(documents))
        self.get_forum_index().commit()

    def remove_forum_posts_from_index(self, forum_post_objects_or_ids):
        for post_object_or_id in forum_post_objects_or_ids:
            if type(post_object_or_id) != Post:
                post_id = post_object_or_id
            else:
                post_id = post_object_or_id.id
            self.get_forum_index().delete(id=post_id)
        self.get_forum_index().commit()

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
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter. This would not be strictly
        # needed because SearchResults and SolrResponseInterpreter are virtually the same, but we do it in this way to
        # conform to SearchEngine.search_sounds definition which must return SearchResults
        results = SolrResponseInterpreter(self.get_forum_index().search(**query.as_dict()).raw_response)
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
        query.set_dismax_query('')
        filter_query = 'username:\"%s\"' % username
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=10, mincount=1)
        results = SolrResponseInterpreter(self.get_sounds_index().search(**query.as_dict()).raw_response)
        return results.facets['tag']

    def get_pack_tags(self, username, pack_name):
        query = SolrQueryPySolr()
        query.set_dismax_query('')
        filter_query = 'username:\"%s\" pack:\"%s\"' % (username, pack_name)
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=20, mincount=1)
        results = SolrResponseInterpreter(self.get_sounds_index().search(**query.as_dict()).raw_response)
        return results.facets['tag']
