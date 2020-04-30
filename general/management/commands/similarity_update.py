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

import yaml

from similarity.client import Similarity
from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them. Use option --force " \
           "to force reindex ALL sounds. Use option -l to limit the maximum number of sounds to index " \
           "(to avoid collapsing similarity if using crons). Use option -ev to only index sounds with a specific" \
           "essentia extractor version. For exampel: python manage.py similarity_update -ev 0.3 -l 1000"

    def add_arguments(self, parser):
        parser.add_argument(
            '-ev', '--extractor_version',
            action='store',
            dest='freesound_extractor_version',
            default='0.3',
            help='Only index sounds analyzed with specific Freesound Extractor version')

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
        freesound_extractor_version = options['freesound_extractor_version']
        console_logger.info(limit, freesound_extractor_version)

        if options['force']:
            to_be_added = Sound.objects.filter(analysis_state='OK', moderation_state='OK').order_by('id')[:limit]
        else:
            to_be_added = Sound.objects.filter(
                analysis_state='OK', similarity_state='PE', moderation_state='OK').order_by('id')[:limit]

        N = len(to_be_added)
        for count, sound in enumerate(to_be_added):

            # Check if sound analyzed using the desired extractor
            if freesound_extractor_version:
                try:
                    data = yaml.load(open(sound.locations('analysis.statistics.path')), Loader=yaml.cyaml.CLoader)
                except:
                    console_logger.info('Sound with id %i was not indexed (no yaml file found when checking for '
                                        'extractor version)' % sound.id)
                    continue

                if data:
                    if 'freesound_extractor' in data['metadata']['version']:
                        if data['metadata']['version']['freesound_extractor'] != freesound_extractor_version:
                            console_logger.info(
                                'Sound with id %i was not indexed (it was analyzed with extractor version %s)'
                                % (sound.id, data['metadata']['version']['freesound_extractor']))
                            continue
                    else:
                        console_logger.info('Sound with id %i was not indexed (it was analyzed with an unknown '
                                            'extractor)' % sound.id)
                        continue
                else:
                    console_logger.info('Sound with id %i was not indexed (most probably empty yaml file)' % sound.id)
                    continue

            try:
                if options['indexing_server']:
                    result = Similarity.add_to_indeixing_server(sound.id, sound.locations('analysis.statistics.path'))
                else:
                    result = Similarity.add(sound.id, sound.locations('analysis.statistics.path'))
                    sound.set_similarity_state('OK')
                    sound.invalidate_template_caches()
                console_logger.info("%s (%i of %i)" % (result, count+1, N))

            except Exception as e:
                if not options['indexing_server']:
                    sound.set_similarity_state('FA')
                console_logger.error('Unexpected error while trying to add sound (id: %i, %i of %i): \n\t%s'
                                     % (sound.id, count+1, N, str(e)))

        self.log_start({'n_sounds_added': to_be_added.count()})
