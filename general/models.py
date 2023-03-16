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

from comments.models import Comment
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import models
from favorites.models import Favorite
from ratings.models import SoundRating
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

class OrderedModel(models.Model):
    order = models.PositiveIntegerField(editable=False)

    def save(self, *args, **kwargs):
        if not self.id:
            try:
                self.order = self.__class__.objects.all().order_by("-order")[0].order + 1
            except IndexError:
                self.order = 0
        super().save(*args, **kwargs)

    def change_order(self):
        model_type_id = ContentType.objects.get_for_model(self.__class__).id
        model_id = self.id
        kwargs = {"direction": "up", "model_type_id": model_type_id, "model_id": model_id}
        url_up = reverse("admin-move", kwargs=kwargs)
        kwargs["direction"] = "down"
        url_down = reverse("admin-move", kwargs=kwargs)
        return mark_safe(f'<a href="{url_up}">up</a> | <a href="{url_down}">down</a>')
    change_order.short_description = 'Move'
    change_order.admin_order_field = 'order'
                
    @staticmethod
    def move(direction, model_type_id, model_id):
        try:
            ModelClass = ContentType.objects.get(id=model_type_id).model_class()

            current_model = ModelClass.objects.get(id=model_id)
            
            if direction == "down":
                swap_model = ModelClass.objects.filter(order__gt=current_model.order).order_by("order")[0]
            elif direction == "up":
                swap_model = ModelClass.objects.filter(order__lt=current_model.order).order_by("-order")[0]
            
            current_model.order, swap_model.order = swap_model.order, current_model.order

            current_model.save()
            swap_model.save()
        except IndexError:
            pass
        except ModelClass.DoesNotExist:
            pass

    class Meta:
        ordering = ["order"]
        abstract = True
