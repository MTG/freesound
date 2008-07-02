# -*- coding: utf-8 -*-
from comments.models import Comment
from django.contrib.contenttypes import generic
from django.db import models
from favorites.models import Favorite
from geotags.models import GeoTag
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