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
import random

from django.conf import settings

from sounds.models import SoundAnalysis
from sounds.templatetags.bst_category import bst_taxonomy_category_names_to_category_key
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
            '--create-codes',
            action='store_true',
            dest='create_codes',
            default=False,
            help='If set, create an extra file for "category code" descriptor which is based of a combination of "category" and "subcategory" descriptors.')
          

    def handle(self, *args, **options):
        self.log_start()

        output_dir = os.path.join(settings.DATA_PATH, 'audio_descriptors_values')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # First get all SoundAnalysis ids for the consolidated analyzer
        # In this way if new sound analyses are added while we are exporting we will not include them
        sound_analysis_objects_ids = SoundAnalysis.objects.filter(analyzer=settings.CONSOLIDATED_ANALYZER_NAME).values_list('id', flat=True)
        sound_analysis_objects_ids = list(sound_analysis_objects_ids)


        if options['limit'] is not None and len(sound_analysis_objects_ids) > int(options['limit']):
            sound_analysis_objects_ids = random.sample(sound_analysis_objects_ids, int(options['limit']))

        # First of all export sound ID as a "reference" descriptor so we know to which sounds the values correspond to
        sound_ids = list(SoundAnalysis.objects.filter(id__in=sound_analysis_objects_ids).values_list(f'sound_id', flat=True))
        json.dump(sound_ids, open(os.path.join(output_dir, 'sound_id.json'), 'w'))

        # Now iterate over all the requested descriptors and export their values
        descriptor_names = options['names'].split(',') if options['names'] != '*' else None
        if descriptor_names is None:
            descriptor_names = settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES
        else:
            descriptor_names = [name for name in descriptor_names if name in settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES]

        for descriptor_name in descriptor_names:
            console_logger.info(f'Exporting values for descriptor: {descriptor_name}')
            descriptor_values = list(SoundAnalysis.objects.filter(id__in=sound_analysis_objects_ids)
                                     .values_list(f'analysis_data__{descriptor_name}', flat=True))
            
            output_file_path = os.path.join(output_dir, f'{descriptor_name}.json')
            json.dump(descriptor_values, open(output_file_path, 'w'))
            console_logger.info(f'Exported {len(descriptor_values)} values for descriptor {descriptor_name} to {output_file_path}')

        if options['create_codes']:
            categories = list(SoundAnalysis.objects.filter(id__in=sound_analysis_objects_ids)
                                     .values_list(f'analysis_data__category', flat=True))
            subcategories = list(SoundAnalysis.objects.filter(id__in=sound_analysis_objects_ids)
                                     .values_list(f'analysis_data__subcategory', flat=True))
            category_codes = [bst_taxonomy_category_names_to_category_key(cat, subcat) for cat, subcat in zip(categories, subcategories)]
            output_file_path = os.path.join(output_dir, f'category_code.json')
            json.dump(category_codes, open(output_file_path, 'w'))
            console_logger.info(f'Exported {len(category_codes)} values for category code descriptor to {output_file_path}')
        
        self.log_end()
