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
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from accounts.models import Profile, UserFlag


def delete_active_user(modeladmin, request, queryset):
    for user in queryset:
        user.profile.change_ownership_of_user_content()
        user.delete()

delete_active_user.short_description = "Delete selected users, preserve posts, threads and comments"


def delete_active_user_preserve_sounds(modeladmin, request, queryset):
    for user in queryset:
        user.profile.change_ownership_of_user_content(include_sounds=True)
        user.delete()

delete_active_user_preserve_sounds.short_description = "Delete selected users, preserve all their content"


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
    actions = (delete_active_user, delete_active_user_preserve_sounds, )
    list_display = ('username', 'email')
    list_filter = ()
    ordering = ('id', )

admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)

