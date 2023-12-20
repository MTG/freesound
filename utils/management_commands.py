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
import sys
import time

from django.core.management.base import BaseCommand

commands_logger = logging.getLogger('commands')


class LoggingBaseCommand(BaseCommand):
    """
    Custom base class for Django management commands which facilitates logging when the command is executed. Logging
    is formatted in a specific way that allows our logging server (graylog) to parse and understand the data and
    be able to make show plots and statistics.

    This base class should be used instead of django.core.management.base.BaseCommand whenever there's an interest
    for logging the start time and end time of a management command, including the time it took to execute and
    (possibly) some extra metadata.

    Management command using this base class are expected to call self.log_start() and self.log_end() at the beginning
    and end of the self.handle() function respectively. Optionally, a `data` dictionary can be passed to both
    self.log_start() and self.log_end() so that the data will be also sent (and parsed) in the logging server. This
    data dictionary must be JSON serializable.
    """

    start_time = None
    command_name = None

    def find_command_name(self):
        for count, arg in enumerate(sys.argv):
            if 'manage.py' in arg:
                return sys.argv[count + 1]
        return None

    def log_start(self, data=None):
        self.start_time = time.time()
        self.command_name = self.find_command_name()
        if data is None:
            data = {}
        data['command'] = self.command_name
        commands_logger.info(f'Started management command ({json.dumps(data)})')

    def log_end(self, data=None):
        if data is None:
            data = {}
        if self.start_time:
            data['work_time'] = round(time.time() - self.start_time)
        data['command'] = self.command_name or self.find_command_name()
        commands_logger.info(f'Finished management command ({json.dumps(data)})')
