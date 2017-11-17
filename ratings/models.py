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

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import F, Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class SoundRating(models.Model):
    user = models.ForeignKey(User)

    rating = models.IntegerField()
    sound = models.ForeignKey('sounds.Sound', null=True, related_name='ratings')
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s rated %s: %d" % (self.user, self.sound, self.rating)

    class Meta:
        unique_together = (('user', 'sound'),)
        ordering = ('-created',)


@receiver(post_delete, sender=SoundRating)
def post_delete_rating(sender, instance, **kwargs):
    try:
        with transaction.atomic():
            instance.sound.num_ratings = F('num_ratings') - 1
            rating = SoundRating.objects.filter(
                    sound_id=instance.sound_id).aggregate(Avg('rating')).values()[0]
            if not rating:
                rating = 0
            instance.sound.avg_rating = rating
            instance.sound.save()
    except ObjectDoesNotExist:
        pass


@receiver(post_save, sender=SoundRating)
def update_num_ratings_on_post_insert(**kwargs):
    with transaction.atomic():
        instance = kwargs['instance']
        if kwargs['created']:
            instance.sound.num_ratings = F('num_ratings') + 1
        instance.sound.avg_rating = SoundRating.objects.filter(
                sound_id=instance.sound_id).aggregate(Avg('rating')).values()[0]
        instance.sound.save()
