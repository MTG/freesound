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
import logging
import os

from django.conf import settings
from django.utils import timezone

from freesound.celery import get_queues_task_counts
from sounds.models import SoundAnalysis
from utils.management_commands import LoggingBaseCommand


console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = """This command iterates over the list of all CONSOLIDATED_AUDIO_DESCRIPTORS and exports a list with all values for
    every descriptor in a distinct JSON file. This is used to compute statistics (histograms) for audio descriptors and generate
    plots for the API documentation.
    """

    def add_arguments(self, parser):
        
        parser.add_argument(
            '--limit',
            action='store',
            dest='limit',
            default=None,
            help='Maximum number of values to be included per descriptor. If less than the number of sounds, a random subset will be used.')
        
        parser.add_argument(
            '--names',
            action='store',
            dest='names',
            default="*",
            help='Descriptor names, separated by commas. Use * to include all descriptors.')
        
        parser.add_argument(
            '--remove_nones',
            action='store_true',
            dest='remove_nones',
            default=False,
            help='If set, None values will be removed from the exported lists.')


    def handle(self, *args, **options):
        self.log_start()

        output_dir = os.path.join(settings.DATA_PATH, 'audio_descriptors_values')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        descriptor_names = options['names'].split(',') if options['names'] != '*' else None
        if descriptor_names is None:
            descriptor_names = settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES
        else:
            descriptor_names = [name for name in descriptor_names if name in settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES]

        for descriptor_name in descriptor_names:
            console_logger.info(f'Exporting values for descriptor: {descriptor_name}')
            descriptor_values = list(SoundAnalysis.objects.filter(analyzer=settings.CONSOLIDATED_ANALYZER_NAME)
                                     .values_list(f'analysis_data__{descriptor_name}', flat=True))
            if options['remove_nones']:
                descriptor_values = [value for value in descriptor_values if value is not None]
            if options['limit'] is not None and len(descriptor_values) > int(options['limit']):
                import random
                descriptor_values = random.sample(descriptor_values, int(options['limit']))
            output_file_path = os.path.join(output_dir, f'{descriptor_name}.json')
            json.dump(descriptor_values, open(output_file_path, 'w'))
            console_logger.info(f'Exported {len(descriptor_values)} values for descriptor {descriptor_name} to {output_file_path}')
        
        self.log_end()
