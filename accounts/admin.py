# -*- coding: utf-8 -*-
from django.contrib import admin
from accounts.models import Profile

from forum.models import Post, Thread
from comments.models import Comment
from sounds.models import Sound,DeletedSound
from accounts.models import User
import settings


from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

def delete_active_user(modeladmin, request, queryset):
    deleted_user = User.objects.get(id=settings.DELETED_USER_ID)     
    for user in queryset:
        for post in Post.objects.filter(author=user):
            post.author = deleted_user
            post.save()
                
        for thread in Thread.objects.filter(author=user):
            thread.author = deleted_user
            thread.save()
                    
        for comment in Comment.objects.filter(user=user):
            comment.user = deleted_user
            comment.save()

        for sound in DeletedSound.objects.filter(user=user):
            sound.user = deleted_user
            sound.save()
        user.delete()
        
delete_active_user.description="Delete user(s), not posts etc"  

UserAdmin.actions.append(delete_active_user)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'geotag') 
    list_display = ('user', 'home_page', 'signature', 'is_whitelisted')
    ordering = ('id', )
    list_filter = ('is_whitelisted', 'wants_newsletter', )
    search_fields = ('=user__username', )

admin.site.register(Profile, ProfileAdmin)
