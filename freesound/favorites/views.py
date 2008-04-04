# Create your views here.

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Favorite(models.Model):
    user = models.ForeignKey(User)
    
    content_type = models.ForeignKey(ContentType) # to identify the table
    object_id = models.PositiveIntegerField(db_index=True) # the id
    content_object = generic.GenericForeignKey() # the actual object    
    
    created = models.DateTimeField()