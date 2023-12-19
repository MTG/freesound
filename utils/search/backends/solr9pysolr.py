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

import re
import pysolr
from django.conf import settings

from utils.search.backends import solr555pysolr

SOLR_FORUM_URL = f"{settings.SOLR9_BASE_URL}/forum"
SOLR_SOUNDS_URL = f"{settings.SOLR9_BASE_URL}/freesound"


class Solr9PySolrSearchEngine(solr555pysolr.Solr555PySolrSearchEngine):
    def __init__(self, sounds_index_url=None, forum_index_url=None):
        if sounds_index_url is None:
            sounds_index_url = SOLR_SOUNDS_URL
        if forum_index_url is None:
            forum_index_url = SOLR_FORUM_URL
        self.sounds_index_url = sounds_index_url
        self.forum_index_url = forum_index_url


    def get_sounds_index(self):
        if self.sounds_index is None:
            self.sounds_index = pysolr.Solr(
                self.sounds_index_url,
                encoder=solr555pysolr.FreesoundSoundJsonEncoder(),
                results_cls=solr555pysolr.SolrResponseInterpreter,
                always_commit=True
            )
        return self.sounds_index

    def get_forum_index(self):
        if self.forum_index is None:
            self.forum_index = pysolr.Solr(
                self.forum_index_url,
                encoder=solr555pysolr.FreesoundSoundJsonEncoder(),
                results_cls=solr555pysolr.SolrResponseInterpreter,
                always_commit=True
            )
        return self.forum_index


    def search_process_filter(self, query_filter, only_sounds_within_ids=False, only_sounds_with_pack=False):
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
        query_filter = solr555pysolr.add_solr_suffix_to_dynamic_fieldnames_in_filter(query_filter)

        # When filtering by the created field, use the `created_range` DateRangeType field instead
        # which include the ability to filter on exact values and ranges of values.
        if 'created:' in query_filter:
            query_filter = query_filter.replace('created:', 'created_range:')

        # If we only want sounds with packs and there is no pack filter, add one
        if only_sounds_with_pack and not 'pack:' in query_filter:
            query_filter += ' pack:*'

        if 'geotag:"Intersects(' in query_filter:
            # Replace geotag:"Intersects(<MINIMUM_LONGITUDE> <MINIMUM_LATITUDE> <MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>)"
            #    with geotag:["<MINIMUM_LATITUDE>, <MINIMUM_LONGITUDE>" TO "<MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>"]
            query_filter = re.sub('geotag:"Intersects\((.+?) (.+?) (.+?) (.+?)\)"', r'geotag:["\2,\1" TO "\4,\3"]', query_filter)

        query_filter = solr555pysolr.search_filter_make_intersection(query_filter)

        # When calculating results form clustering, the "only_sounds_within_ids" argument is passed and we filter
        # our query to the sounds in that list of IDs.
        if only_sounds_within_ids:
            sounds_within_ids_filter = ' OR '.join(['id:{}'.format(sound_id) for sound_id in only_sounds_within_ids])
            if query_filter:
                query_filter += ' AND ({})'.format(sounds_within_ids_filter)
            else:
                query_filter = '({})'.format(sounds_within_ids_filter)

        return query_filter