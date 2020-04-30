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
import sys
import time

from django.core.management.base import BaseCommand


commands_logger = logging.getLogger('commands')


class LoggingBaseCommand(BaseCommand):

    start_time = None
    command_name = None

    def find_command_name(self):
        for count, arg in enumerate(sys.argv):
            if arg == 'manage.py':
                return sys.argv[count + 1]
        return None

    def log_start(self, data=None):
        self.start_time = time.time()
        self.command_name = self.find_command_name()
        if data is None:
            data = {}
        data['command'] = self.command_name
        commands_logger.info('Started management command ({0})'.format(json.dumps(data)))

    def log_end(self, data=None):
        command_name = os.path.basename(__file__)
        if data is None:
            data = {}
        if self.start_time:
            data['work_time'] = time.time() - self.start_time
        data['command'] = self.command_name or self.find_command_name()
        commands_logger.info('Finished management command ({0})'.format(json.dumps(data)))
