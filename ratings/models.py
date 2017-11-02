# -*- coding: utf-8 -*-

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
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import F, Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class Rating(models.Model):
    user = models.ForeignKey(User)

    rating = models.IntegerField()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = fields.GenericForeignKey()

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s rated %s - %s: %d" % (self.user, self.content_type, self.content_type, self.rating)

    class Meta:
        unique_together = (('user', 'content_type', 'object_id'),)
        ordering = ('-created',)


@receiver(post_delete, sender=Rating)
def post_delete_rating(sender, instance, **kwargs):
    try:
        instance.content_object.num_ratings = F('num_ratings') - 1
        rating = Rating.objects.filter(
                content_type_id=instance.content_type_id,
                object_id=instance.object_id).aggregate(Avg('rating')).values()[0]
        if rating is None:
            rating = 0
        instance.content_object.avg_rating = rating
        instance.content_object.save()
    except ObjectDoesNotExist:
        pass


@receiver(post_save, sender=Rating)
def update_num_ratings_on_post_insert(**kwargs):
    instance = kwargs['instance']
    if kwargs['created']:
        instance.content_object.num_ratings = F('num_ratings') + 1
    instance.content_object.avg_rating = Rating.objects.filter(
            content_type_id=instance.content_type_id,
            object_id=instance.object_id).aggregate(Avg('rating')).values()[0]
    instance.content_object.save()
