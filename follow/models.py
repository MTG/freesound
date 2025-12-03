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
from django.db import models


class FollowingUserItem(models.Model):
    user_from = models.ForeignKey(User, related_name="following_items", on_delete=models.CASCADE)
    user_to = models.ForeignKey(User, related_name="follower_items", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_from} following {self.user_to}"

    class Meta:
        verbose_name_plural = "Users"
        unique_together = ("user_from", "user_to")


class FollowingQueryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # TODO: refactor this to name it "tags" instead of "query"
    query = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} following tag '{self.query}'"

    def get_slash_tags(self):
        return self.query.replace(" ", "/")

    def get_split_tags(self):
        return self.query.split(" ")

    def get_space_tags(self):
        return self.query

    class Meta:
        verbose_name_plural = "Tags"
        unique_together = ("user", "query")
