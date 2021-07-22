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

from django.conf import settings
from django.core.management.base import BaseCommand

from sounds.models import Sound, SoundAnalysis

console_logger = logging.getLogger("console")

# Dictionary that links simple names and versions of the analyzers to their actual docker images
# Needs to be updated everytime a new analyzer or analyzer version is added
ANALYZERS_DICT = {
    "fs-essentia:1": "fs-essentia-extractor:20210525_9a3bd10",
    "audio-commons:1": "ac-extractor:20210525_9a3bd10",
    "audioset-vggish:1": "audioset-vggish-extractor:20210615_f44030e"
}


class Command(BaseCommand):

    help = """Checks if there are sounds that have not been analyzed by the analyzers defined in the Analysis 
    Configuration File (or that are analyzed with older versions) and send jobs to the analysis workers if needed"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--analysis_config_file',
            action='store',
            required=True,
            help='Absolute path to the analysis configuration file')
        parser.add_argument(
            '--status',
            action="store_true",
            help='Flag to print the main status of the analysis. It does not trigger any analysis.')

    def handle(self, *args, **options):
        # Read config json
        with open(options['analysis_config_file']) as json_file:
            config_file = json.load(json_file)
        
        # Print information about the already analyzed sounds if the status flag exists
        if options['status']:
            n_analyzed = len(SoundAnalysis.objects.all())
            n_sounds = len(Sound.objects.all())
            n_analyzers = len(config_file['analyzer:version'])
            total2analyze = n_sounds * n_analyzers
            console_logger.info("{0} analysis performed. In total, there can be {1} ({2} sounds x {3} analyzers in config file).".format(n_analyzed, total2analyze, n_sounds, n_analyzers))
            
            # Count number of analysis to be performed
            n_analysis = 0
            for a in config_file['analyzer:version']:
                # Check all sounds available
                for s in Sound.objects.all():
                    _, version = a.split(":")
                    if not SoundAnalysis.objects.filter(sound=s, analyzer=ANALYZERS_DICT[a], analyzer_version=version).exists():
                        n_analysis += 1
            console_logger.info("{0} analysis to be performed.".format(n_analysis))

            # List all saved analysis
            console_logger.info("List of analyzed sounds:")
            for a in SoundAnalysis.objects.all():
                console_logger.info(json.dumps({'sound_id': a.sound.id, 'SoundAnalysis_id': a.id,
                                                'analyzer': a.analyzer, 'analyzer_version': a.analyzer_version
                                                }))
            
        else:
            console_logger.info("Analysis configuration file: {0}".format(config_file))
            for a in config_file['analyzer:version']:
                # Check all sounds available
                for s in Sound.objects.all():
                    # if the combination sound-analyzer-version does not exist, trigger analysis
                    _, version = a.split(":")
                    if not SoundAnalysis.objects.filter(sound=s, analyzer=ANALYZERS_DICT[a], analyzer_version=version).exists():
                        console_logger.info(
                            "Triggering analysis of sound {0} with analyzer {1}.".format(s.id, ANALYZERS_DICT[a]))
                        s.analyze_v2(analyzer=ANALYZERS_DICT[a], force=True)
