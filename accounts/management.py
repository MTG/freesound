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

from accounts import models as auth_models
from django.contrib.auth.models import User
from accounts.models import Profile
from south.signals import post_migrate
import logging

logger = logging.getLogger("web")


def create_super_profile(**kwargs):
    for user in User.objects.filter(profile=None): # create profiles for all users that don't have profiles yet
        logger.info("\tcreating profile for super user: %s",  user)
        profile = Profile(user=user)
        profile.save()

post_migrate.connect(create_super_profile, sender=auth_models)