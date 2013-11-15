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

from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
    help = "Check the status of solr and gaia index and compare it to the Freesound database. Report about sychronization errors and change is_index_dirty and similarity_state of sounds that need to be reindexed."
    option_list = BaseCommand.option_list + (
    make_option('-nc','--no-changes',
        dest='no-changes',
        action='store_true',
        default=False,
        help='Using the option --no-changes the is_index_dirty and similarity_state sound fields will not be modified.'),
    )

    def handle(self,  *args, **options):
        pass
