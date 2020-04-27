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
import logging

from django.core.management.base import BaseCommand
from django.urls import reverse


console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = "Build Beast Whoosh static files using npm while passing some required Django settings"

    def handle(self, **options):
        """
        This management command will use NPM to build static files and while set a number of Django settings as
        environment variables so that these can be used in code.
        """
        variables = {
            'QUERY_SUGGESTIONS_URL': reverse('query-suggestions')
        }
        variables_for_command = ' '.join(['{0}={1}'.format(key, value) for key, value in variables.items()])
        build_static_command = variables_for_command + ' npm run build'
        console_logger.info('Building static files with command:\n' + build_static_command)
        os.system(build_static_command)
