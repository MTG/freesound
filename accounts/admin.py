# -*- coding: utf-8 -*-

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

from django.contrib import admin
from accounts.models import Profile, UserFlag

from forum.models import Post, Thread
from comments.models import Comment
from sounds.models import Sound,DeletedSound
from accounts.models import User
from django.conf import settings

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

class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'geotag')
    list_display = ('user', 'home_page', 'signature', 'is_whitelisted')
    ordering = ('id', )
    list_filter = ('is_whitelisted', 'wants_newsletter', )
    search_fields = ('=user__username', )

admin.site.register(Profile, ProfileAdmin)


class UserFlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'reporting_user', 'content_type')
    list_display = ('user', 'reporting_user', 'content_type')
admin.site.register(UserFlag, UserFlagAdmin)


class FreesoundUserAdmin(UserAdmin):
    search_fields = ('username', 'email')
    actions = (delete_active_user, )

admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)

