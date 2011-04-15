# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import SocialModel
from geotags.models import GeoTag
from utils.sql import DelayedQueryExecuter
from django.conf import settings

class ProfileManager(models.Manager):
    def random_uploader(self):
        import random
        
        user_count = User.objects.filter(profile__num_sounds__gte=1).count()

        if user_count:
            offset = random.randint(0, user_count - 1)
            return User.objects.filter(profile__num_sounds__gte=1)[offset:offset+1][0]
        else:
            return None

class Profile(SocialModel):
    user = models.OneToOneField(User)
    
    about = models.TextField(null=True, blank=True, default=None)
    home_page = models.URLField(null=True, blank=True, default=None)
    signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    has_avatar = models.BooleanField(default=False)

    wants_newsletter = models.BooleanField(default=True, db_index=True)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    
    last_action_time = models.DateTimeField(null=True, blank=True, default=None)
    
    num_sounds = models.PositiveIntegerField(editable=False, default=0)
    num_posts = models.PositiveIntegerField(editable=False, default=0)
    
    objects = ProfileManager()
    
    def __unicode__(self):
        return self.user.username
    
    @models.permalink
    def get_absolute_url(self):
        return ('account', (smart_unicode(self.user.username),))
    
    def get_avatar_path(self):
        if self.has_avatar:
            path_s = "%s%d/%d_%s.jpg" % (settings.PROFILE_IMAGES_URL, self.user.id/1000, self.user.id, "s")
            path_m = "%s%d/%d_%s.jpg" % (settings.PROFILE_IMAGES_URL, self.user.id/1000, self.user.id, "m")
            path_l = "%s%d/%d_%s.jpg" % (settings.PROFILE_IMAGES_URL, self.user.id/1000, self.user.id, "l")
        else:
            path_s = settings.MEDIA_URL + "images/32x32_avatar.png"
            path_m = settings.MEDIA_URL + "images/40x40_avatar.png"
            path_l = settings.MEDIA_URL + "images/40x40_avatar.png"
            
        return dict(path_s=path_s, path_m=path_m, path_l=path_l)
    
    def get_tagcloud(self):
        return DelayedQueryExecuter("""
            select
                tags_tag.name as name,
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