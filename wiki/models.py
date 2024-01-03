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
from django.utils.encoding import smart_str
from django.urls import reverse


class Page(models.Model):
    name = models.CharField(max_length=256, db_index=True)

    def __str__(self):
        return self.name

    def content(self):
        return Content.objects.filter(page=self).latest()

    def get_absolute_url(self):
        return reverse("wiki-page", args=[smart_str(self.name)])


class Content(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    title = models.CharField(max_length=250)
    body = models.TextField()
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ('-created',)
        get_latest_by = 'created'

    def __str__(self):
        return self.title
