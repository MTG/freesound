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
import re
import math
from datetime import date, datetime
from collections import defaultdict

import pysolr
from django.conf import settings

from forum.models import Post
from sounds.models import Sound, SoundAnalysis
from utils.text import remove_control_chars
from utils.search import SearchEngineBase, SearchResults, SearchEngineException
from utils.search.backends.solr_common import SolrQuery, SolrResponseInterpreter
from utils.similarity_utilities import get_similarity_search_target_vector, get_l2_normalized_vector


SOLR_FORUM_URL = f"{settings.SOLR5_BASE_URL}/forum"
SOLR_SOUNDS_URL = f"{settings.SOLR5_BASE_URL}/freesound"

USE_COLLAPSE_AND_EXPAND_QUERY_PARSER = True  # Note that changing this requies a reindex of the Solr index to used sound IDs as pack_gropuing when sounds have no pack

# Mapping from freesound sound field names to solr sound field names
FIELD_NAMES_MAP = {
    settings.SEARCH_SOUNDS_FIELD_ID: 'id',
    settings.SEARCH_SOUNDS_FIELD_NAME: 'original_filename',
    settings.SEARCH_SOUNDS_FIELD_TAGS: {'field': 'tag', 'facet': 'tagfacet'},
    settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 'description',
    settings.SEARCH_SOUNDS_FIELD_USER_NAME: {'field': 'username', 'facet': 'username_facet'},
    settings.SEARCH_SOUNDS_FIELD_PACK_NAME: 'pack',
    settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING: 'pack_grouping',
    settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: 'samplerate',
    settings.SEARCH_SOUNDS_FIELD_BITRATE: 'bitrate',
    settings.SEARCH_SOUNDS_FIELD_BITDEPTH: 'bitdepth',
    settings.SEARCH_SOUNDS_FIELD_TYPE: {'field': 'type', 'facet': 'type_facet'},
    settings.SEARCH_SOUNDS_FIELD_CHANNELS: 'channels',
    settings.SEARCH_SOUNDS_FIELD_LICENSE_NAME: 'license'
}

# Create a reverse field name map that will be useful to get the original freesound field name from a solr field name
# Include the facet-specific field names as well
REVERSE_FIELD_NAMES_MAP = {}
for key, value in FIELD_NAMES_MAP.items():
    if isinstance(value, dict):
        REVERSE_FIELD_NAMES_MAP[value['field']] = key
        REVERSE_FIELD_NAMES_MAP[value['facet']] = key
    else:
        REVERSE_FIELD_NAMES_MAP[value] = key

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

# Some dynamic field types need to have alternative field versions that work with facets. In that case an extra suffix is added.
SOLR_DYNAMIC_FIELD_FACET_EXTRA_SUFFIX = '_f'

# Generate a map of dynamic fields that will be used to index the output of analyzers. In ANALYZERS_CONFIGURATION, a list of descriptors is
# defined along with their type. This map will be used to generate the dynamic field names that will be used to index the descriptors
SOLR_DYNAMIC_FIELDS_MAP = {}
for analyzer, analyzer_data in settings.ANALYZERS_CONFIGURATION.items():
    if 'descriptors_map' in analyzer_data:
        descriptors_map = analyzer_data['descriptors_map']
        for _, db_descriptor_key, descriptor_type in descriptors_map:
            if descriptor_type is not None:
                SOLR_DYNAMIC_FIELDS_MAP[db_descriptor_key] = '{}{}'.format(
                    db_descriptor_key, SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[descriptor_type])


def get_solr_fieldname_from_freesound_fieldname(field_name, facet=False, skip_dynamic_field_suffix=False):
    # Get solr field name from the field name map. If the field is to be used for faceting, it is possible that a 
    # special field name is used
    name_or_dict = FIELD_NAMES_MAP.get(field_name, field_name)
    if isinstance(name_or_dict, dict):
        if facet and 'facet' in name_or_dict:
            solr_field_name = name_or_dict['facet']
        else:
            solr_field_name = name_or_dict['field']
    else:
        solr_field_name = name_or_dict

    # Add the suffix to the field name if it is a dynamic field
    if not skip_dynamic_field_suffix:
        solr_field_name = SOLR_DYNAMIC_FIELDS_MAP.get(solr_field_name, solr_field_name)
    
        # If the field is a list of strings and we want to use it for faceting, we need to add the extra suffix
        if solr_field_name.endswith("_ls") and facet:
            solr_field_name += SOLR_DYNAMIC_FIELD_FACET_EXTRA_SUFFIX
    
    return solr_field_name


def get_solr_facet_fieldname_from_freesound_fieldname(solr_field_name):
    return get_solr_fieldname_from_freesound_fieldname(solr_field_name, facet=True)
    

def get_freesound_fieldname_from_solr_fieldname(solr_field_name):

    # Remove special dynamic field faced suffix
    if solr_field_name.endswith(f"_ls{SOLR_DYNAMIC_FIELD_FACET_EXTRA_SUFFIX}"):
        solr_field_name = solr_field_name[:-len(SOLR_DYNAMIC_FIELD_FACET_EXTRA_SUFFIX)]

    # Remove the rest of dynamic field suffixes
    for suffix in SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.values():
        if solr_field_name.endswith(suffix):
            solr_field_name = solr_field_name[:-len(suffix)]

    # Now get the original freesound field name using the reserve map
    return REVERSE_FIELD_NAMES_MAP.get(solr_field_name, solr_field_name)


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
SORT_OPTIONS_MAP_FORUM = {
    settings.SEARCH_FORUM_SORT_OPTION_THREAD_DATE_FIRST: "thread_created desc",
    settings.SEARCH_FORUM_SORT_OPTION_DATE_NEW_FIRST: "post_created desc",
}

SOLR_VECTOR_FIELDS_DIMENSIONS_MAP = {
    100: 'sim_vector100',
    512: 'sim_vector512',
}


def get_solr_dense_vector_search_field_name(dimensions, l2_norm=False):
    base_field_name = SOLR_VECTOR_FIELDS_DIMENSIONS_MAP.get(dimensions, None)
    if base_field_name is None:
        return None
    if l2_norm:
        return f'{base_field_name}_l2'
    return base_field_name


SOLR_SOUND_FACET_DEFAULT_OPTIONS = {
    'limit': 5,
    'type': 'terms',
    'sort': 'count desc',
    'mincount': 1,
    'missing': False
}

SOLR_DOC_CONTENT_TYPES = {
    'sound': 's',
    'similarity_vector': 'v'
}


class FreesoundSoundJsonEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        elif isinstance(value, date):
            return value.strftime('%Y-%m-%dT00:00:00.000Z')

        return json.JSONEncoder.default(self, value)


class Solr555PySolrSearchEngine(SearchEngineBase):
    solr_base_url = settings.SOLR5_BASE_URL
    sounds_index = None
    forum_index = None

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
                encoder=FreesoundSoundJsonEncoder(),
                results_cls=SolrResponseInterpreter,
                search_handler="fsquery",
                always_commit=True
            )
        return self.sounds_index

    def get_forum_index(self):
        if self.forum_index is None:
            self.forum_index = pysolr.Solr(
                self.forum_index_url,
                encoder=FreesoundSoundJsonEncoder(),
                results_cls=SolrResponseInterpreter,
                search_handler="fsquery",
                always_commit=True
            )
        return self.forum_index
    
    # Util functions
    def transform_document_into_update_document(self, document):
        """
        In order to update a document in SOLR, we need to send a document with the same ID of the document we want to update and the
        list of fields with the values we want to set wrapped in a {'set': value} dictionary. This function transforms a normal solr
        document with {key:value} pairs into a document that will update all the fields. This is useful when we only want to update some
        fields but not remove those not updated. Using this method we can update similarity-related sound fields and the rest of the
        fields independently.
        """
        new_document = {'id': document['id']}
        new_document.update({key: {'set': value} for key, value in document.items() if key != 'id'})
        return new_document

    def convert_sound_to_search_engine_document(self, sound, include_analyzer_output=False):
        """
        TODO: Document that this includes remove_control_chars due to originally sending XML. not strictly necessary when submitting
            to json (and also, freesound model code fixes this), but keep it in to ensure that docs are clean.
        TODO: Assert that sound object is correct?
        """
        document = {}

        # Basic sound fields
        keep_fields = ['username', 'created', 'is_explicit', 'is_remix', 'num_ratings', 'channels', 'md5',
                    'was_remixed', 'original_filename', 'duration', 'num_downloads', 'filesize']
        for key in keep_fields:
            document[key] = getattr(sound, key)
        if sound.type == '':
            document["type"] = "wav"
        else:
            document["type"] = sound.type
        document["original_filename"] = remove_control_chars(getattr(sound, "original_filename"))
        document["description"] = remove_control_chars(getattr(sound, "description"))
        document["tag"] = list({t.lower() for t in getattr(sound, "tag_array")})
        document["license"] = sound.license.name

        if document["num_ratings"] >= settings.MIN_NUMBER_RATINGS:
            document["avg_rating"] = getattr(sound, "avg_rating")
        else:
            document["avg_rating"] = 0

        if sound.pack:
            document["pack"] = remove_control_chars(sound.pack.name)
            document["pack_grouping"] = str(sound.pack.id) + "_" + remove_control_chars(sound.pack.name)
        else:
            if not USE_COLLAPSE_AND_EXPAND_QUERY_PARSER:
                # If we're not using the collapse query parser, we need to set the pack_grouping field to the sound ID
                # for sounds that don't have a pack. This is so that we get the correct total count of packs/individual sounds
                # when grouping by pack. With the collapse query parser, this is not needed because the nullPolicy=expand will
                # precisely treat sounds without packs as a group of their own.
                document["pack_grouping"] = str(getattr(sound, "id"))


        document["is_geotagged"] = False
        if hasattr(sound, "geotag"):
            document["is_geotagged"] = True
            if not math.isnan(sound.geotag.lon) and not math.isnan(sound.geotag.lat):
                document["geotag"] = str(sound.geotag.lon) + " " + str(sound.geotag.lat)

        document["in_remix_group"] = getattr(sound, "was_remixed") or getattr(sound, "is_remix")

        document["bitdepth"] = getattr(sound, "bitdepth") if getattr(sound, "bitdepth") else 0
        document["bitrate"] = getattr(sound, "bitrate") if getattr(sound, "bitrate") else 0
        document["samplerate"] = int(getattr(sound, "samplerate")) if getattr(sound, "samplerate") else 0

        document["comment"] = [remove_control_chars(comment_text) for comment_text in getattr(sound, "comments_array")]
        document["num_comments"] = getattr(sound, "num_comments")
 
        locations = sound.locations()
        document["waveform_path_m"] = locations["display"]["wave"]["M"]["path"]
        document["waveform_path_l"] = locations["display"]["wave"]["L"]["path"]
        document["spectral_path_m"] = locations["display"]["spectral"]["M"]["path"]
        document["spectral_path_l"] = locations["display"]["spectral"]["L"]["path"]
        document["preview_path"] = locations["preview"]["LQ"]["mp3"]["path"]
        
        # Analyzer's output
        sound_analysis_dict = {an.analyzer: an.analysis_data for an in sound.analyses.all()}
        for analyzer_name, analyzer_info in settings.ANALYZERS_CONFIGURATION.items():
            if 'descriptors_map' in analyzer_info:
                analysis_data = sound_analysis_dict.get(analyzer_name, None)
                if analysis_data is not None:
                    # If analysis is present, index all existing analysis fields using SOLR dynamic fields depending on
                    # the value type (see SOLR_DYNAMIC_FIELDS_SUFFIX_MAP) so solr knows how to treat when filtering, etc.
                    for key, value in analysis_data.items():
                        if isinstance(value, list):
                            # Make sure that the list is formed by strings
                            value = [f'{item}' for item in value]
                        suffix = SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.get(type(value), None)
                        if suffix:
                            document[f'{key}{suffix}'] = value
                            if suffix == '_ls':
                                # For dynamic fields of type "list of strings", we also need to set an extra field that
                                # will be used for faceting
                                document[f'{key}{suffix}{SOLR_DYNAMIC_FIELD_FACET_EXTRA_SUFFIX}'] = value

        # Category and subcategory fields
        # When adding fields from analyzers output, automatically predicted category and subcategory will be added. However,
        # if a sound does indeed have that field annotated by a user, then we want to use the user provided-value and not the
        # automatically-generated one
        if sound.bst_category is not None:
            user_provided_category, user_provided_subcategory = sound.category_names
            if user_provided_category is not None:
                document[f'{settings.SEARCH_SOUNDS_FIELD_CATEGORY}{SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[str]}'] = user_provided_category
            if user_provided_subcategory is not None:
                document[f'{settings.SEARCH_SOUNDS_FIELD_SUBCATEGORY}{SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[str]}'] = user_provided_subcategory

        # Finally add the sound ID and content type
        document.update({'id': sound.id, 'content_type': SOLR_DOC_CONTENT_TYPES['sound']})

        return document

    def add_similarity_vectors_to_documents(self, sound_objects, documents):
        similarity_data = defaultdict(list)
        sound_ids = [s.id for s in sound_objects]
        sound_objects_dict = {s.id: s for s in sound_objects}
        for analyzer_name, config_options in settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS.items():
            # If we should index similarity data, add it to the documents
            vector_field_name = get_solr_dense_vector_search_field_name(config_options['vector_size'], config_options.get('l2_norm', False))

            if vector_field_name is None:
                # If the vector size is not supported, then we can't index the vectors generated by the requested analyzer
                continue

            vector_property_name = config_options['vector_property_name']
            for sa in SoundAnalysis.objects.filter(sound_id__in=sound_ids, analyzer=analyzer_name, analysis_status="OK"):
                similarity_vectors_per_analyzer_per_sound=[]
                if sa.analysis_data is not None and vector_property_name in sa.analysis_data:
                    data = sa.analysis_data
                else:
                    data = sa.get_analysis_data_from_file()
                if data is not None:
                    if data.get(vector_property_name, None) is not None:
                        vector_data =data[vector_property_name][0:config_options['vector_size']]
                        if config_options.get('l2_norm', False):
                            # Normalize the vector to have unit length
                            vector_data = get_l2_normalized_vector(vector_data)

                        sim_vector_document_data = {
                            'content_type': SOLR_DOC_CONTENT_TYPES['similarity_vector'],
                            'analyzer': sa.analyzer,
                            'timestamp_start': 0,  # This will be used in the future if analyzers generate multiple sound vectors
                            'timestamp_end': -1,  # This will be used in the future if analyzers generate multiple sound vectors
                            vector_field_name: vector_data
                        }
                        # Because we still want to be able to group by pack when matching sim vector documents (sound child documents),
                        # we add the pack_grouping field here as well. In the future we might be able to optimize this if we can tell solr
                        # to group results by the field value of a parent document (just like we do to compute facets)
                        if getattr(sound_objects_dict[sa.sound_id], "pack_id"):
                            sim_vector_document_data['pack_grouping_child'] = str(getattr(sound_objects_dict[sa.sound_id], "pack_id")) + "_" + remove_control_chars(
                                getattr(sound_objects_dict[sa.sound_id], "pack_name"))
                        else:
                            sim_vector_document_data['pack_grouping_child'] = str(getattr(sound_objects_dict[sa.sound_id], "id"))
                        similarity_vectors_per_analyzer_per_sound.append(sim_vector_document_data)
                if similarity_vectors_per_analyzer_per_sound:
                    similarity_data[sa.sound_id] += similarity_vectors_per_analyzer_per_sound
        
        # Add collected vectors to the documents created as child documents
        for document in documents:
            if document['id'] in similarity_data:
                document['similarity_vectors'] = similarity_data[document['id']]

    def convert_post_to_search_engine_document(self, post):
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

    def add_solr_suffix_to_dynamic_fieldnames_in_filter(self, query_filter):
        """Processes a filter string containing field names and replaces the occurrences of fieldnames that match with
        descriptor names from the descriptors_map of different configured analyzers with updated fieldnames with
        the required SOLR dynamic field suffix. This is needed because fields from analyzers are indexed as dynamic
        fields which need to end with a specific suffi that SOLR uses to learn about the type of the field and how it
        should treat it.
        """
        for raw_fieldname, solr_fieldname in SOLR_DYNAMIC_FIELDS_MAP.items():
            query_filter = query_filter.replace(
                f'{raw_fieldname}:', f'{solr_fieldname}:')
        return query_filter
        
    def search_process_sort(self, sort, forum=False):
        """Translates sorting criteria to solr sort criteria and add extra criteria if sorting by ratings.

        If order by rating, when rating is the same sort also by number of ratings.

        Args:
            sort (str): sorting criteria as defined in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB.
            forum (bool, optional): use the forum sort options map instead of the standard sort map

        Returns:
            List[str]: list containing the sorting field names list for the search engine.
        """
        search_map = SORT_OPTIONS_MAP_FORUM if forum else SORT_OPTIONS_MAP
        if sort in [sort_web_name for sort_web_name, _ in search_map.items()]:
            if search_map[sort] == "avg_rating desc" or search_map[sort] == "avg_rating asc":
                sort = [search_map[sort], "num_ratings desc"]
            else:
                sort = [search_map[sort]]
        else:
            sort = [search_map[settings.SEARCH_FORUM_SORT_DEFAULT if forum else settings.SEARCH_SOUNDS_SORT_DEFAULT]]
        return sort

    def search_filter_make_intersection(self, query_filter):
        # In solr 4, fq="a:1 b:2" will take the AND of these two filters, but in solr 5+, this will use OR
        # fq=a:1&fq=b:2 can be used to take an AND, however we don't support this syntax
        # The AND behaviour can be approximated by using fq="+a:1 +b:2", therefore we add a + to the beginning of each 
        # filter item to force AND. Because we use Dismax query parser, if we have a filter like fq="a:1 OR b:2" which will
        # be converted to fq="+a:1 OR +b:2" by this function, this will still correctly use the OR operator (this would not
        # be the case with standard lucene query parser).
        # NOTE: for the filter names we match "a-zA-Z_" instead of using \w as using \w would cause problems for filters
        # which have date ranges inside.
        # NOTE: in the future filter handling should be refactored and we should use a proper filter parser
        # that allows us to define our own filter syntax and then represent filters as some intermediate structure that can later
        # be converted to valid lucene/dismax syntax.
        query_filter = re.sub(r'\b([a-zA-Z_]+:)', r'+\1', query_filter)
        query_filter = re.sub(r'(\+)\1+', r'\1', query_filter)  # This is to avoid having multiple + in a row if user already has added them
        query_filter = re.sub(r'(-)\+', r'\1', query_filter) # Removes added '+' when user has included a negation '-'
        if len(query_filter) > 0 and query_filter[-1] == '+':
            query_filter = query_filter[:-1]
        return query_filter

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
        query_filter = self.add_solr_suffix_to_dynamic_fieldnames_in_filter(query_filter)

        # If we only want sounds with packs and there is no pack filter, add one
        if only_sounds_with_pack and 'pack:' not in query_filter:
            query_filter += ' pack:*'

        if 'geotag:"Intersects(' in query_filter:
            # Replace geotag:"Intersects(<MINIMUM_LONGITUDE> <MINIMUM_LATITUDE> <MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>)"
            #    with geotag:["<MINIMUM_LATITUDE>, <MINIMUM_LONGITUDE>" TO "<MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>"]
            query_filter = re.sub(r'geotag:"Intersects\((.+?) (.+?) (.+?) (.+?)\)"', r'geotag:["\2,\1" TO "\4,\3"]', query_filter)

        query_filter = self.search_filter_make_intersection(query_filter)

        # When calculating results form clustering, the "only_sounds_within_ids" argument is passed and we filter
        # our query to the sounds in that list of IDs.
        if only_sounds_within_ids:
            sounds_within_ids_filter = ' OR '.join([f'id:{sound_id}' for sound_id in only_sounds_within_ids])
            if query_filter:
                query_filter += f' AND ({sounds_within_ids_filter})'
            else:
                query_filter = f'({sounds_within_ids_filter})'

        return query_filter

    def force_sounds(self, query_dict):
        # Add an extra filter to the query parameters to make sure these return sound documents only
        current_fq = query_dict['fq']
        if isinstance(current_fq, list):
            query_dict.update({'fq': current_fq + [f'content_type:{SOLR_DOC_CONTENT_TYPES["sound"]}']}) 
        else:
            query_dict.update({'fq': [current_fq, f'content_type:{SOLR_DOC_CONTENT_TYPES["sound"]}']}) 
        return query_dict

    # Sound methods
    def add_sounds_to_index(self, sound_objects, update=False, include_similarity_vectors=False):
        # Generate basic documents for Solr
        documents = [self.convert_sound_to_search_engine_document(s) for s in sound_objects]
        # If required, collect similarity vectors from all configured analyzers
        if include_similarity_vectors:
            self.add_similarity_vectors_to_documents(sound_objects, documents)
        if update:
            documents = [self.transform_document_into_update_document(d) for d in documents]
        try:
            self.get_sounds_index().add(documents)
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def update_similarity_vectors_in_index(self, sound_objects):
        """Create an update document to add only similarity vectors to sounds that already exist in the index"""
        documents = [{'id': sound.id, 'content_type': SOLR_DOC_CONTENT_TYPES['sound']} for sound in sound_objects]
        self.add_similarity_vectors_to_documents(sound_objects, documents)
        documents = [self.transform_document_into_update_document(d) for d in documents]
        try:
            self.get_sounds_index().add(documents)
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def remove_sounds_from_index(self, sound_objects_or_ids):
        try:
            sound_ids = []
            for sound_object_or_id in sound_objects_or_ids:
                if not isinstance(sound_object_or_id, Sound):
                    sound_ids.append(str(sound_object_or_id))
                else:
                    sound_ids.append(str(sound_object_or_id.id))
            self.get_sounds_index().delete(id=sound_ids)
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def remove_all_sounds(self):
        try:
            self.get_sounds_index().delete(q="*:*")
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def sound_exists_in_index(self, sound_object_or_id):
        if not isinstance(sound_object_or_id, Sound):
            sound_id = sound_object_or_id
        else:
            sound_id = sound_object_or_id.id
        response = self.search_sounds(query_filter=f'id:{sound_id}', offset=0, num_sounds=1)
        return response.num_found > 0
    
    def get_all_sound_ids_from_index(self):
        page_size=2000
        solr_ids = []
        solr_count = None
        current_page = 1
        while solr_count is None or len(solr_ids) < solr_count:
            response = self.search_sounds(sort=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
                                          offset=(current_page - 1) * page_size,
                                          num_sounds=page_size)
            solr_ids += [int(element['id']) for element in response.docs]
            solr_count = response.num_found
            current_page += 1
        return sorted(solr_ids)

    def search_sounds(self, textual_query='', query_fields=None, query_filter='', field_list=['id', 'score'],
                      offset=0, current_page=None, num_sounds=settings.SOUNDS_PER_PAGE,
                      sort=settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC,
                      group_by_pack=False, num_sounds_per_pack_group=1, facets=None, only_sounds_with_pack=False,
                      only_sounds_within_ids=False, group_counts_as_one_in_facets=False,
                      similar_to=None, similar_to_max_num_sounds=settings.SEARCH_ENGINE_NUM_SIMILAR_SOUNDS_PER_QUERY ,
                      similar_to_analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER):

        query = SolrQuery()

        if similar_to is None:
            # Usual search query, no similarity search
        
            # Process search fields: replace "db" field names by solr field names and set default weights if needed
            if query_fields is None:
                # If no fields provided, use the default
                query_fields = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS
            if isinstance(query_fields, list):
                query_fields = [get_solr_fieldname_from_freesound_fieldname(field_name) for field_name in query_fields]
            elif isinstance(query_fields, dict):
                # Also remove fields with weight <= 0
                query_fields = [(get_solr_fieldname_from_freesound_fieldname(field_name), weight)
                    for field_name, weight in query_fields.items() if weight > 0]

            # Set main query options
            query.set_dismax_query(textual_query, query_fields=query_fields)

        else:
            # Similarity search!
            
            # We fist set an empty query that will return no results and will be used by default if similarity can't be performed
            query.set_query('')
            if similar_to_analyzer in settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS:
                # Similarity search will find documents close to a target vector. This will match "child" sound documents (of content_type "similarity vector")
                config_options = settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS[similar_to_analyzer]
                vector = None
                if isinstance(similar_to, list):
                    vector = similar_to  # we allow vectors to be passed directly
                else:
                    # similar_to should be a sound_id
                    try:
                        sound = Sound.objects.get(id=similar_to)
                    except Sound.DoesNotExist:
                        # Return no results if sound does not exist
                        return SearchResults(num_found=0)
                    vector = get_similarity_search_target_vector(sound.id, analyzer=similar_to_analyzer)       
                vector_field_name = get_solr_dense_vector_search_field_name(config_options['vector_size'], config_options.get('l2_norm', False))
                if vector is not None and vector_field_name is not None:
                    max_similar_sounds = similar_to_max_num_sounds  # Max number of results for similarity search search. Filters are applied before the similarity search, so this number will usually be the total number of results (unless filters are more restrictive)
                    serialized_vector = ','.join([str(n) for n in vector])
                    query.set_query(f'{{!knn f={vector_field_name} topK={max_similar_sounds}}}[{serialized_vector}]')
        
        # Process filter
        query_filter = self.search_process_filter(query_filter,
                                                  only_sounds_within_ids=only_sounds_within_ids,
                                                  only_sounds_with_pack=only_sounds_with_pack)
        
        if similar_to is not None:
            # If doing a similarity query, the filter needs to be further processed so we perform filters based on parent documents
            query_filter_modified = [f'content_type:{SOLR_DOC_CONTENT_TYPES["similarity_vector"]}', f'analyzer:{similar_to_analyzer}']  # Add basic filter to only get similarity vectors from selected analyzer and from child documents (this is because root documents can also have sim vectors)
            top_similar_sounds_as_filter = query.as_kwargs()['q']
            try:
                # Also if target is specified as a sound ID, remove it from the list
                query_filter_modified.append(f'-_nest_parent_:{int(similar_to)}')
                # Update the top_similar_sounds_as_filter so we compensate for the fact that we are removing the target sound from the results
                top_similar_sounds_as_filter=top_similar_sounds_as_filter.replace(f'topK={similar_to_max_num_sounds}', f'topK={similar_to_max_num_sounds + 1}')
            except TypeError:
                # Target is not a sound id, so we don't need to add the filter
                pass
            
            # Also add the NN query as a filter so we don't get past the first similar_to_max_num_sounds results when applying extra filters
            query_filter_modified += [top_similar_sounds_as_filter]  

            # Now add the usual filter, but wrap it in "child of" modifier so it filters on parent documents instead of child documents
            if query_filter:
                query_filter_modified.append(f'{{!child of=\"content_type:{SOLR_DOC_CONTENT_TYPES["sound"]}\"}}({query_filter})')

            # Replace query_filter with the modified version
            query_filter = query_filter_modified

        # Set query options
        if current_page is not None:
            offset = (current_page - 1) * num_sounds
        query.set_query_options(start=offset,
                                rows=num_sounds,
                                field_list=field_list,  # We generally only want the sound IDs of the results as we load data from DB
                                filter_query=query_filter,
                                sort=self.search_process_sort(sort) if not similar_to else ['score desc'])  # In similarity queries, we always sort by distance to target

        # Configure facets
        if facets is not None:
            json_facets = {}
            facet_fields = [get_solr_facet_fieldname_from_freesound_fieldname(field_name) for field_name, _ in facets.items()]
            for field in facet_fields:
                json_facets[field] = SOLR_SOUND_FACET_DEFAULT_OPTIONS.copy()
                json_facets[field]['field'] = field
                if similar_to is not None:
                    # In similarity search we need to set the "domain" facet option to apply them to the parent documents of the child documents we will match
                    json_facets[field]['domain'] = {'blockParent': f'content_type:{SOLR_DOC_CONTENT_TYPES["sound"]}'}
            for field_name, extra_options in facets.items():
                json_facets[get_solr_facet_fieldname_from_freesound_fieldname(field_name)].update(extra_options)
            query.set_facet_json_api(json_facets)

        # Configure grouping
        if group_by_pack:
            if USE_COLLAPSE_AND_EXPAND_QUERY_PARSER:
                current_filter = query.params.get('fq', '')
                field_name = "pack_grouping" if similar_to is None else "pack_grouping_child"
                group_by_pack_filter = f'{{!collapse field={field_name} nullPolicy=expand}}'
                if current_filter:
                    if type(current_filter) is list:
                        query.params['fq'] = current_filter + [group_by_pack_filter]
                    else:
                        query.params['fq'] = [current_filter, group_by_pack_filter]
                else:
                    query.params['fq'] = [group_by_pack_filter]
                query.params['fl'] = query.params['fl'] + f',{field_name}'
                query.params['expand'] = True
                query.params['expand.rows'] = max(0, num_sounds_per_pack_group - 1)  # We return one less sound per pack group because the first sound is used to represent the pack group
            else:
                query.set_group_field(group_field="pack_grouping" if not similar_to else "pack_grouping_child")  
                query.set_group_options(
                    group_func=None,
                    group_query=None,
                    group_start=0,
                    group_limit=num_sounds_per_pack_group,  # This is the number of documents that will be returned for each group.
                    group_offset=0,
                    group_sort=None,
                    group_sort_ingroup=None,
                    group_format='grouped',
                    group_main=False,
                    group_num_groups=True,  # We need to know the number of groups to be able to paginate
                    group_cache_percent=0,
                    group_truncate=group_counts_as_one_in_facets)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter (the response from .search()).
        # We do it in this way to conform to SearchEngine.search_sounds definition which must return SearchResults
        try:
            # Get a dictionary with the query parameters to be sent to SOLR. Take into account that in non-similarity queries, 
            # we need to force the content_type to be "sound" so no child documents (similarity vector documents) are returned
            query_as_kwargs = self.force_sounds(query.as_kwargs()) if similar_to is None else query.as_kwargs()

            if  USE_COLLAPSE_AND_EXPAND_QUERY_PARSER and group_by_pack:
                # If we are using collapse and expand query parser and are grouping by pack, we need to make an extra
                # query to obtain 1) the total number of ungrouped "matches", and 2) facet counts for all sounds and not only
                # the collapsed groups (except if group_counts_as_one_in_facets is True, in which case we are fine with the
                # collapsed facet counts). Event hough we are making two queries, this is still more efficient than making
                # a single query using the "group" method as we were doing before using the collapse and expand query parser.
                
                # Make the initial query to get the collapsed results. Remove facet computation if needed to save query time.
                facets_kwarg = None
                if not group_counts_as_one_in_facets and 'json.facet' in query_as_kwargs:
                    facets_kwarg = query_as_kwargs['json.facet']
                    query_as_kwargs['json.facet'] = {}
                results = self.get_sounds_index().search(**query_as_kwargs)
               
                # Now make the second query in which we get the facets and the total number of results, and remove the "collapse" filter.               
                fq = [fq_element for fq_element in query_as_kwargs['fq'] if 'collapse field' not in fq_element]
                query_as_kwargs['fq'] = fq
                query_as_kwargs['rows'] = 0
                query_as_kwargs['expand'] = False
                if not group_counts_as_one_in_facets and facets_kwarg is not None:
                    query_as_kwargs['json.facet'] = facets_kwarg
                results_extra_query = self.get_sounds_index().search(**query_as_kwargs)
                if not group_counts_as_one_in_facets:
                    results.facets = results_extra_query.facets
                results.non_grouped_number_of_results = results_extra_query.num_found
            else:
                # If we are not using collapse and expand query parser (and/or not grouping by pack), just run the query.
                results = self.get_sounds_index().search(**query_as_kwargs)
            
            # Facets returned in results use the corresponding solr fieldnames as keys. We want to convert them to the
            # original fieldnames so that the rest of the code can use them without knowing about the solr fieldnames.
            results.facets = {get_freesound_fieldname_from_solr_fieldname(facet_name): data for facet_name, data in results.facets.items()}

            # Solr uses a string for the id field, but django uses an int. Convert the id in all results to int
            # before use to avoid issues
            for d in results.docs:
                # Get the sound ids from the results
                d["id"] = int(d["id"] if similar_to is None else d["id"].split('/')[0])

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
        except pysolr.SolrError as e:
            raise SearchEngineException(e)


    def get_random_sound_id(self):
        query = SolrQuery()
        rand_key = random.randint(1, 10000000)
        sort = ['random_%d asc' % rand_key]
        filter_query = 'is_explicit:0'
        query.set_query("*:*")
        query.set_query_options(start=0, rows=1, field_list=["id"], filter_query=filter_query, sort=sort)
        try:
            response = self.get_sounds_index().search(search_handler="select", **self.force_sounds(query.as_kwargs()))
            docs = response.docs
            if docs:
                return int(docs[0]['id'])
            return 0
        except pysolr.SolrError as e:
            raise SearchEngineException(e)
        
    def get_num_sim_vectors_indexed_per_analyzer(self):
        results = {}
        for analyzer_name in settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS.keys():
            query = SolrQuery()
            filter_query = f'analyzer:"{analyzer_name}" content_type:"v"'
            query.set_query("*:*")
            query.set_query_options(start=0, rows=1, field_list=["id"], filter_query=filter_query)
            query.set_group_field("_nest_parent_")
            query.set_group_options()
            try:
                response = self.get_sounds_index().search(search_handler="select", **query.as_kwargs())
                results[analyzer_name] = {
                    'num_sounds': response.num_found,
                    'num_vectors': response.non_grouped_number_of_results
                }
            except pysolr.SolrError as e:
                raise SearchEngineException(e)
        return results

    # Forum posts methods
    def add_forum_posts_to_index(self, forum_post_objects):
        documents = [self.convert_post_to_search_engine_document(p) for p in forum_post_objects]
        documents = [d for d in documents if d is not None]
        try:
            self.get_forum_index().add(documents)
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def remove_forum_posts_from_index(self, forum_post_objects_or_ids):
        try:
            for post_object_or_id in forum_post_objects_or_ids:
                if not isinstance(post_object_or_id, Post):
                    post_id = post_object_or_id
                else:
                    post_id = post_object_or_id.id

                self.get_forum_index().delete(id=str(post_id))
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def remove_all_forum_posts(self):
        try:
            self.get_forum_index().delete(q="*:*")
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def forum_post_exists_in_index(self, forum_post_object_or_id):
        if not isinstance(forum_post_object_or_id, Post):
            post_id = forum_post_object_or_id
        else:
            post_id = forum_post_object_or_id.id
        response = self.search_forum_posts(query_filter=f'id:{post_id}', offset=0, num_posts=1)
        return response.num_found > 0

    def search_forum_posts(self, textual_query='', query_filter='', sort=settings.SEARCH_FORUM_SORT_DEFAULT, 
                           offset=0, current_page=None, num_posts=settings.FORUM_POSTS_PER_PAGE, group_by_thread=True):
        query = SolrQuery()
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
                                            "score",
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
                                sort=self.search_process_sort(sort, forum=True))

        if group_by_thread:
            query.set_group_field("thread_title_grouped")
            query.set_group_options(group_limit=30)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter (the response from .search()).
        # We do it in this way to conform to SearchEngine.search_sounds definition which must return SearchResults
        try:
            results = self.get_forum_index().search(**query.as_kwargs())
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
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    # Tag clouds methods
    def get_user_tags(self, username):
        query = SolrQuery()
        query.set_query('*:*')
        filter_query = f'username:"{username}"'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        tag_facet_field_name = get_solr_facet_fieldname_from_freesound_fieldname(get_solr_fieldname_from_freesound_fieldname(settings.SEARCH_SOUNDS_FIELD_TAGS))
        query.add_facet_fields(tag_facet_field_name)
        query.set_facet_options(tag_facet_field_name, limit=10, mincount=1)
        try:
            results = self.get_sounds_index().search(**self.force_sounds(query.as_kwargs()))
            return results.facets[tag_facet_field_name]
        except pysolr.SolrError as e:
            raise SearchEngineException(e)

    def get_pack_tags(self, username, pack_name):
        query = SolrQuery()
        query.set_dismax_query('*:*')
        filter_query = f'username:\"{username}\" pack:\"{pack_name}\"'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        tag_facet_field_name = get_solr_facet_fieldname_from_freesound_fieldname(get_solr_fieldname_from_freesound_fieldname(settings.SEARCH_SOUNDS_FIELD_TAGS))
        query.add_facet_fields(tag_facet_field_name)
        query.set_facet_options(tag_facet_field_name, limit=20, mincount=1)
        try:
            results = self.get_sounds_index().search(**self.force_sounds(query.as_kwargs()))
            return results.facets[tag_facet_field_name]
        except pysolr.SolrError as e:
            raise SearchEngineException(e)
