from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Image(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=512)
    filename_base = models.CharField(max_length=512)

    content_type = models.ForeignKey(ContentType) # to identify the table
    object_id = models.PositiveIntegerField(db_index=True) # the id
    content_object = generic.GenericForeignKey() # the actual object    
        
    # --- moderation ----------------------------------------
    MODERATION_STATE_CHOICES = (
                                ("PE",_('Pending')),
                                ("OK",_('OK')),
                               )
    
    moderation_state = models.CharField(db_index=True, max_length=3, choices=MODERATION_STATE_CHOICES)
    moderation_date = models.DateTimeField(null=True, blank=True)
    
    created = models.DateTimeField()
    modified = models.DateTimeField()   