# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import SocialModel
from geotags.models import GeoTag
from utils.sql import DelayedQueryExecuter

class Profile(SocialModel):
    user = models.OneToOneField(User)
    
    about = models.TextField(null=True, blank=True, default=None)
    home_page = models.URLField(null=True, blank=True, default=None)
    signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)

    wants_newsletter = models.BooleanField(default=True, db_index=True)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    
    last_action_time = models.DateTimeField(null=True, blank=True, default=None)
    
    num_sounds = models.PositiveIntegerField(editable=False, default=0)
    num_posts = models.PositiveIntegerField(editable=False, default=0)
    
    def __unicode__(self):
        return self.user.username
    
    @models.permalink
    def get_absolute_url(self):
        return ('account', (smart_unicode(self.user.username),))
    
    def get_tagcloud(self):
        return DelayedQueryExecuter("""
            select
                tags_tag.name as tag,
                X.c as count
            from (
                select
                    tag_id,
                    count(*) as c
                from tags_taggeditem
                where user_id=%d
                group by tag_id
                order by c
                desc limit 10
            ) as X
            left join tags_tag on tags_tag.id=X.tag_id
            order by tags_tag.name;""" % self.user.id)

    class Meta(SocialModel.Meta):
        ordering = ('-user__date_joined', )