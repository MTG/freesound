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

import os
import json
import logging
import math
from django.core.management.base import BaseCommand
from django.conf import settings
from sounds.models import Sound, SoundAnalysis

logger = logging.getLogger("console")


def value_is_valid(value):
    # Postgres JSON data field can not store float values of nan or inf. These vlaues should have never
    # been outputted by the Audio Commons extractor in the first place. We use this function here and skip
    # indexing key/value pairs where the value is not valid for Postgres JSON data fields.
    if type(value) == float:
        return not math.isinf(value) and not math.isnan(value)
    return True


class Command(BaseCommand):

    help = 'Read Audio Commons analysis data for Freesound sounds and create corresponding SoundAnalysis objects'

    def add_arguments(self, parser):
        parser.add_argument('--analysis_basedir', type=str, required=True,
                            help='Base directory where to find the analysis files for each sound')
        parser.add_argument('--extractor', type=str, default=settings.AUDIOCOMMONS_EXTRACTOR_NAME,
                            help='Extractor name to be used in the SoundAnalysis object')

    def handle(self, *args, **options):

        # We iterate over all folders and JSON files in the given analysis_basedir.
        # For each file we parse the corresponding Freesound sound id (we know that AudioCommons anlaysis output
        # stores the files with the naming pattern "{sound_id}.json") and create a SoundAnalysis object for the
        # corresponding sound.

        n_analyses_loaded = 0
        n_does_not_exist = 0
        for root, dirnames, filenames in os.walk(options['analysis_basedir']):
            logger.info("Loading analyses from folder %s" % root)
            for filename in filenames:
                if filename.endswith('json'):
                    filepath = os.path.join(root, filename)
                    try:
                        sound_id = int(filename.split('.json')[0])
                        sound = Sound.objects.get(id=sound_id)
                        analysis_data = json.load(open(filepath))
                        ac_descriptor_names = \
                            [name for name, _ in settings.AUDIOCOMMONS_INCLUDED_DESCRIPTOR_NAMES_TYPES]
                        filtered_analysis_data = {key: value for key, value in analysis_data.items()
                                                  if key in ac_descriptor_names and value_is_valid(value)}
                        SoundAnalysis.objects.get_or_create(sound=sound, extractor=options['extractor'],
                                                            analysis_data=filtered_analysis_data)
                        n_analyses_loaded += 1

                    except ValueError:
                        # The file we're trying to open is not a JSON file or does not follow naming pattern
                        # "{sound_id}.json"
                        pass
                    except Sound.DoesNotExist:
                        # Sound does not exist in Freesound, no need to load any data
                        n_does_not_exist += 1
                        pass

        logger.info("Created or updated %i SoundAnalysis objects" % n_analyses_loaded)
        if n_does_not_exist:
            logger.info("Failed to create %i SoundAnalysis objects for sounds that do not exist" % n_does_not_exist)
