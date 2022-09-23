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

from django.conf import settings
from django.core.management.base import BaseCommand

from utils.search import get_search_engine
from utils.search.backends.test_search_engine_backend import TestSearchEngineBackend


console_logger = logging.getLogger("console")

global_write_output = False
global_backend_name = ''
global_output_file = None


class Command(BaseCommand):
    help = 'Test a search engine backend and output test results. To run these tests, a search engine backend is' \
           'expected to be running with some sounds/forum posts indexed in accordance to Sound and Post objects' \
           'from the database. The Freesound development data will work nicely with these tests. After running the' \
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
            raise Exception('Running search engine tests in a production deployment. This should not be done as'
                            'running these tests will modify the contents of the production search engine index'
                            'and leave it in a "wrong" state.')

        # Instantiate search engine
        try:
            search_engine = get_search_engine(backend_class=options['backend_class'])
        except ValueError:
            raise Exception('Wrong backend name format. Should be a path like '
                            'utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine')
        except ImportError as e:
            raise Exception('Backend class to test could not be imported: {}'.format(e))

        console_logger.info('Testing search engine backend: {}'.format(options['backend_class']))
        backend_name = options['backend_class']
        write_output = options['write_output']

        if not options['sound_methods'] and not options['forum_methods']:
            console_logger.info('None of sound methods or forum methods were selected, so nothing will be tested. '
                                'Use the -s, -f or both options to test sound and/or forum methods.')


        backend_test = TestSearchEngineBackend(backend_name, write_output)
        if options['sound_methods']:
            backend_test.test_search_enginge_backend_sounds()

        if options['forum_methods']:
            backend_test.test_search_enginge_backend_forum()
