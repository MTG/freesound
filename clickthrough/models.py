from django.db import models
from sounds.models import Sound

# Create your models here.
class Click(models.Model):
    # Maintain a record of actions (ie soundpreview, sounddownload, packdownload) on the sound
    
    CLICK_TYPES = (('sp','soundpreivew'),
                   ('sd','sounddownload'),
                   ('pd','packdownload'))
    
    sound = models.ForeignKey(Sound,null=True, blank=True, default=None)
    click_type=models.CharField(max_length=2, choices=CLICK_TYPES)
    click_datetime=models.DateField()
    authenticated_session_key=models.CharField(max_length=32, blank=True, default=None)
    searchtime_session_key=models.CharField(max_length=32, blank=True, default=None)
    
class Query(models.Model):
    # models queries for which a sound was included as the results
    
    sounds=models.ManyToManyField(Sound, null=True, blank=True, default=None)
    query_time=models.DateField()
    searchtime_session_key=models.CharField(max_length=32, blank=True, default=None)
    query_text=models.CharField(max_length=200, blank=True, default=None)
    rank_order=models.CharField(max_length=400, blank=True, default=None)
    results_page_no=models.IntegerField()
