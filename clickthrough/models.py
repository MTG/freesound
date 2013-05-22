from django.db import models
from sounds.models import Sound

# Create your models here.
class Query(models.Model):
    # models queries for which a sound was included as the results

    query_time=models.DateTimeField()
    searchtime_session_key=models.CharField(max_length=32)
    query_text=models.CharField(max_length=400, null=True, blank=True, default=None)
    results_shown=models.CharField(max_length=400)
    results_page_no=models.IntegerField(null=True, blank=True)
    advanced=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_tag=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_filename=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_description=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_packname=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_soundid=models.CharField(max_length=1, null=True, blank=True, default='0')
    a_username=models.CharField(max_length=1, null=True, blank=True, default='0')
    sortby=models.CharField(max_length=100, blank=True)
    duration_min=models.IntegerField(default=0,null=True, blank=True)
    duration_max=models.IntegerField(default=1000000,null=True, blank=True)
    is_geotagged=models.CharField(max_length=1, null=True, blank=True, default='0')
    group_by_pack=models.CharField(max_length=1, null=True, blank=True, default='0')
    
class Click(models.Model):
    # Maintain a record of actions (ie soundpreview, sounddownload, packdownload) on the sound
    
    CLICK_TYPES = (('sp','soundpreivew'),
                   ('sd','sounddownload'),
                   ('pd','packdownload'))
    
    sound = models.ForeignKey(Sound,null=True, blank=True, default=None)
    click_type=models.CharField(max_length=2, choices=CLICK_TYPES)
    click_datetime=models.DateTimeField()
    authenticated_session_key=models.CharField(max_length=32,null=True, blank=True, default=None)
    searchtime_session_key=models.CharField(max_length=32,null=True, blank=True, default=None)
    query = models.ForeignKey(Query,null=True)
    
    
class SessionInfo(models.Model):
    session_key=models.CharField(max_length=32,unique=True)
    
