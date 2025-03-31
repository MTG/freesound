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
import sentry_sdk

from django.conf import settings

from similarity.client import Similarity
from sounds.models import Sound, SoundAnalysis
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):
    help = "Take all sounds that have been analyzer but haven't been added to the similarity service yet and add them. " \
           "Use option --force to force reindex ALL sounds. Use option -l to limit the maximum number of sounds to index " \
           "(to avoid collapsing similarity if using crons). Use option -a to only index sounds with a specific" \
           "analyzer name/version. For example: python manage.py similarity_update -a analyzer-name -l 1000"

    def add_arguments(self, parser):
        parser.add_argument(
            '-a', '--analyzer',
            action='store',
            dest='analyzer',
            default=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME,
            help='Only index sounds analyzed with specific anayzer name/version')

        parser.add_argument(
            '-l', '--limit',
            action='store',
            dest='limit',
            default=1000,
            help='Maximum number of sounds to index')

        parser.add_argument(
            '-f', '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Reindex all sounds regardless of their similarity state')

        parser.add_argument(
            '-i', '--indexing_server',
            action='store_true',
            dest='indexing_server',
            default=False,
            help='Send files to the indexing server instead of the main similarity server')

    def handle(self,  *args, **options):
        self.log_start()

        limit = int(options['limit'])
        analyzer_name = options['analyzer']
        console_logger.info("limit: %s, analyzer: %s", limit, analyzer_name)

        sound_ids_analyzed_with_analyzer_ok = \
            list(SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="OK")
                                      .order_by('id').values_list('sound_id', flat=True))
        if options['force']:
            sound_ids_to_be_added = sound_ids_analyzed_with_analyzer_ok[:limit]
        else:
            sound_ids_similarity_pending =  list(Sound.public.filter(similarity_state='PE').values_list('id', flat=True))
            sound_ids_to_be_added = list(set(sound_ids_similarity_pending).intersection(sound_ids_analyzed_with_analyzer_ok))[:limit]

        N = len(sound_ids_to_be_added)
        to_be_added = sorted(Sound.objects.filter(id__in=sound_ids_to_be_added), key=lambda x: x.id)
        n_added = 0
        n_failed = 0
        for count, sound in enumerate(to_be_added):
            try:
                if options['indexing_server']:
                    result = Similarity.add_to_indeixing_server(sound.id, sound.locations('analysis.statistics.path'))
                else:
                    result = Similarity.add(sound.id, sound.locations('analysis.statistics.path'))
                    sound.set_similarity_state('OK')
                    sound.invalidate_template_caches()
                n_added += 1
                console_logger.info("%s (%i of %i)" % (result, count+1, N))

            except Exception as e:
                if not options['indexing_server']:
                    sound.set_similarity_state('FA')
                n_failed += 1
                console_logger.info('Unexpected error while trying to add sound (id: %i, %i of %i): \n\t%s'
                                     % (sound.id, count+1, N, str(e)))
                sentry_sdk.capture_exception(e)

        self.log_end({'n_sounds_added': n_added, 'n_sounds_failed': n_failed})
