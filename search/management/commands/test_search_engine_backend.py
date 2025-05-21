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

import logging
import os
import json
import datetime
from django.conf import settings
from django.core.management.base import BaseCommand

from search import solrapi
from utils.search import get_search_engine
from utils.search.backends.test_search_engine_backend import TestSearchEngineBackend


console_logger = logging.getLogger("console")

global_write_output = False
global_backend_name = ''
global_output_file = None


class Command(BaseCommand):
    help = 'Test a search engine backend and output test results. To run these tests, a search engine backend is ' \
           'expected to be running. A new core is created for these tests and is populated with some with some ' \
           'sounds/forum posts. The Freesound development data will work nicely with these tests. After running the' \
           'tests, DB contents will not be changed, but it could happen that the search engine index is not left' \
           'in the exact same state. Therefore, this command SHOULD NOT be run in a production database.' \
           '' \
           'What is being tested with this command is that a SearchEngine API responds as expected to the API ' \
           'definition and therefore should not raise unexpected errors when being used in Freesound. The contents' \
           'of the expected search results are only tested in some cases when these can be well specified (e.g. the' \
           'sorting of results is tested when sorting by, eg, downloads count, but not when sorting by score). Also' \
           'things like whether facets are well calculated or not are not tested, but the faceting API is.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-b', '--backend',
            action='store',
            dest='backend_class',
            default=settings.SEARCH_ENGINE_BACKEND_CLASS,
            help='Path to the backend class to test, eg: utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine')

        parser.add_argument(
            '--force',
            action='store_true',
            dest='force_cleanup',
            default=False,
            help='Delete the test cores after running the tests')

        parser.add_argument(
            '-s', '--sound_methods',
            action='store_true',
            dest='sound_methods',
            default=False,
            help='Test sound-related methods of the SearchEngine')

        parser.add_argument(
            '-f', '--forum_methods',
            action='store_true',
            dest='forum_methods',
            default=False,
            help='Test forum post-related methods of the SearchEngine')

        parser.add_argument(
            '-w', '--write_output',
            action='store_true',
            dest='write_output',
            default=False,
            help='Save the query results to a file')

    def handle(self, *args, **options):

        if not settings.DEBUG:
            raise Exception('Running search engine tests in a production deployment. This should not be done as '
                            'running these tests will modify the contents of the production search engine index '
                            'and leave it in a "wrong" state.')

        # Instantiate search engine
        backend_class_name = options['backend_class']
        write_output = options['write_output']
        test_sounds = options['sound_methods']
        test_forum = options['forum_methods']
        force_cleanup = options['force_cleanup']

        try:
            search_engine = get_search_engine(
                backend_class=backend_class_name
            )
        except ValueError:
            raise Exception('Wrong backend name format. Should be a path like '
                            'utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine')
        except ImportError as e:
            raise Exception(f'Backend class to test could not be imported: {e}')

        console_logger.info(f"Testing search engine backend: {backend_class_name}")



        if not options['sound_methods'] and not options['forum_methods']:
            console_logger.info('None of sound methods or forum methods were selected, so nothing will be tested. '
                                'Use the -s, -f or both options to test sound and/or forum methods.')
            return


        today = datetime.datetime.now().strftime('%Y%m%d')
        freesound_temp_collection_name = f"engine_test_freesound_{today}"
        forum_temp_collection_name = f"engine_test_forum_{today}"

        # Create API instances for both collections
        freesound_api = solrapi.SolrManagementAPI(search_engine.solr_base_url, freesound_temp_collection_name)
        forum_api = solrapi.SolrManagementAPI(search_engine.solr_base_url, forum_temp_collection_name)

        if test_sounds and force_cleanup and freesound_api.collection_exists():
            freesound_api.delete_collection()
        if test_forum and force_cleanup and forum_api.collection_exists():
            forum_api.delete_collection()

        schema_directory = os.path.join('.', "utils", "search", "schema")
        freesound_schema_definition = json.load(open(os.path.join(schema_directory, "freesound.json")))
        forum_schema_definition = json.load(open(os.path.join(schema_directory, "forum.json")))
        delete_default_fields_definition = json.load(open(os.path.join(schema_directory, "delete_default_fields.json")))

        if test_sounds:
            freesound_api.create_collection_and_schema(delete_default_fields_definition, freesound_schema_definition, "username")
        if test_forum:
            forum_api.create_collection_and_schema(delete_default_fields_definition, forum_schema_definition, "thread_id")

        sounds_index_url = f'{search_engine.solr_base_url}/solr/{freesound_temp_collection_name}'
        forum_index_url = f'{search_engine.solr_base_url}/solr/{forum_temp_collection_name}'

        backend_test = TestSearchEngineBackend(backend_class_name, write_output, sounds_index_url=sounds_index_url, forum_index_url=forum_index_url)
        if test_sounds:
            backend_test.test_search_engine_backend_sounds()

        if test_forum:
            backend_test.test_search_engine_backend_forum()

        if force_cleanup:
            if test_sounds:
                freesound_api.delete_collection()
            if test_forum:
                forum_api.delete_collection()
