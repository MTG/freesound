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
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.db import models

from favorites.models import Favorite
from tags.models import TaggedItem


class SocialModel(models.Model):
    tags = fields.GenericRelation(TaggedItem)
    fans = fields.GenericRelation(Favorite)

    class Meta:
        abstract = True

class AkismetSpam(SocialModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    spam = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
