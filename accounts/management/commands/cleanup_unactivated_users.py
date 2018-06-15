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
from django.contrib.auth.models import User
from accounts.models import EmailBounce
import logging

logger = logging.getLogger('console')


class Command(BaseCommand):
    help = 'Removes unactivated users with invalid emails'

    def handle(self, *args, **options):
        bounces = EmailBounce.objects.filter(type__in=EmailBounce.TYPES_INVALID, user__is_active=False)
        users = User.objects.filter(id__in=bounces.values_list('user', flat=True))
        total, details = users.delete()
        deleted_users = details.get('auth.Users', 0)
        logger.info('Deleted {} users'.format(deleted_users))
