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

from django.core.management import call_command
from django.test import TestCase


class GeneralManagementCommandTestCase(TestCase):
    """Tests for the managment commands under the general app"""

    def test_report_count_statuses(self):
        # TODO
        # 1) create sound/pack/user/post objects and manually set counts to be wrong
        # 2) run command
        # 3) check that counts are ok
        # 4) manually set the counts to something wrong
        # 5) run command with -n option
        # 6) check that counts are still wrong
        # 7) run command with -d option
        # 8) check that all counts are ok except for download related ones
        # 9) run command
        # 10) check that all counts are ok
        call_command('report_count_statuses', '-nd')
