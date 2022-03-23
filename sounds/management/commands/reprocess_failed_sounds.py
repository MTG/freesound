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

from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand


console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = """Gets a list of sounds that failed processing (or did not fininsh processing successfully) and re-sends them to processing"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action="store_true",
            help="Using this jobs will not be triggered but only information printed on screen.")
    

    def handle(self, *args, **options):
        self.log_start()
        n_sent = 0
        qs = Sound.objects.filter(processing_state="FA")
        console_logger.info('Will send {} sounds to processing'.format(qs.count()))
        for sound in qs:
            if not options['dry_run']:
                was_sent = sound.process()
                if was_sent:
                    n_sent += 1
        self.log_end({'n_sent_to_processing': n_sent})
