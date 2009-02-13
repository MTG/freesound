# -*- coding: utf-8 -*-
from comments.models import Comment
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models
from favorites.models import Favorite
from images.models import Image
from ratings.models import Rating
from tags.models import TaggedItem

class SocialModel(models.Model):
    tags = generic.GenericRelation(TaggedItem)
    comments = generic.GenericRelation(Comment)
    ratings = generic.GenericRelation(Rating)
    fans = generic.GenericRelation(Favorite)
    images = generic.GenericRelation(Image)

    class Meta:
        abstract = True
        

class OrderedModel(models.Model):
    order = models.PositiveIntegerField(editable=False)

    def save(self):
        if not self.id:
            try:
                self.order = self.__class__.objects.all().order_by("-order")[0].order + 1
            except IndexError:
                self.order = 0
        super(OrderedModel, self).save()

    def change_order(self):
        model_type_id = ContentType.objects.get_for_model(self.__class__).id
        model_id = self.id
        kwargs = {"direction": "up", "model_type_id": model_type_id, "model_id": model_id}
        url_up = reverse("admin-move", kwargs=kwargs)
        kwargs["direction"] = "down"
        url_down = reverse("admin-move", kwargs=kwargs)
        return '<a href="%s">up</a> | <a href="%s">down</a>' % (url_up, url_down)
    change_order.allow_tags = True
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