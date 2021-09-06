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
            '--dry_run',
            action="store_true",
            help='Flag to print the main status of the analysis. It does not trigger any analysis.')

    def handle(self, *args, **options):
        # Read config json
        with open(options['analysis_config_file']) as json_file:
            config_file = json.load(json_file)

        # Print information about the already analyzed sounds if the dry_run flag exists
        n_analyzed = SoundAnalysis.objects.all().count()
        n_sounds = Sound.objects.all().count()
        n_analyzers = len(config_file['analyzers'])
        total2analyze = n_sounds * n_analyzers
        # print headers of columns
        console_logger.info("{: >44} {: >11} {: >11} {: >11} {: >11}".format(
            *['analyzer name |', '# ok |', '# failed |', '# skipped |', '# missing']))
        # print row with total numbers
        console_logger.info("{: >44} {: >11} {: >11} {: >11} {: >11}".format(
            *['total |', '{0} |'.format(n_analyzed), '0 |', '0 |', total2analyze]))

        # Count number of analysis done with each analyzer
        for a in config_file['analyzers']:
            analyzer, version = a.split(":")
            analyzed = SoundAnalysis.objects.filter(analyzer=analyzer, analyzer_version=version).count()
            missing = n_sounds-analyzed
            # print row with more info
            console_logger.info("{: >44} {: >11} {: >11} {: >11} {: >11}".format(
                *[a+' |', '{0} |'.format(analyzed), '0 |', '0 |', missing]))

        if not options['dry_run']:
            console_logger.info("Analysis configuration file: {0}".format(config_file))
            for a in config_file['analyzers']:
                # Check all sounds available
                for s in Sound.objects.all():
                    # if the combination sound-analyzer-version does not exist, trigger analysis
                    analyzer, version = a.split(":")
                    if not SoundAnalysis.objects.filter(sound=s, analyzer=analyzer, analyzer_version=version).exists():
                        console_logger.info(
                            "Triggering analysis of sound {0} with analyzer {1}.".format(s.id, analyzer))
                        s.analyze_v2(analyzer=analyzer, force=True)
