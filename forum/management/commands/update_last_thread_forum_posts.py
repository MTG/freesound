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

from forum.models import Forum, Thread
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """Updates last_post property of all Thread and Forum objects to make sure these
    do not get out of sync."""

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--dry",
            action="store_true",
            dest="dry",
            default=False,
            help="Dry run: do not perform any changes to the database",
        )

    def handle(self, *args, **kwargs):
        dry = kwargs["dry"]
        self.log_start()

        num_threads_updated = 0
        for thread in Thread.objects.filter(last_post=None):
            if not dry:
                thread.set_last_post(commit=True)
            num_threads_updated += 1

        num_forums_updated = 0
        for forum in Forum.objects.filter(last_post=None):
            if not dry:
                forum.set_last_post(commit=True)
            num_forums_updated += 1

        console_logger.info(f"Updated last_post for {num_threads_updated} threads and {num_forums_updated} forums.")

        self.log_end({"num_threads_updated": num_threads_updated, "num_forums_updated": num_forums_updated})
