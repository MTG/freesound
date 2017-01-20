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
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from accounts.models import Profile, UserFlag
from django_object_actions import DjangoObjectActions
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages


def disable_active_user(modeladmin, request, queryset):
    for user in queryset:
        user.profile.delete_user(remove_sounds=True)

disable_active_user.short_description = "'Soft' delete selected users, preserve posts, threads and comments (delete sounds)"


def disable_active_user_preserve_sounds(modeladmin, request, queryset):
    for user in queryset:
        user.profile.delete_user()

disable_active_user_preserve_sounds.short_description = "'Soft' delete selected users, preserve sounds and everything else"


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


class FreesoundUserAdmin(DjangoObjectActions, UserAdmin):
    search_fields = ('username', 'email')
    actions = (disable_active_user, disable_active_user_preserve_sounds, )
    list_display = ('username', 'email')
    list_filter = ()
    ordering = ('id', )

    def full_delete(self, request, obj):
        # For now just redirect to default admin delete action
        return HttpResponseRedirect(reverse('admin:auth_user_delete', args=[obj.id]))
    full_delete.label = "Full delete user"
    full_delete.short_description = 'Completely delete user from db'

    def delete_include_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            obj.profile.delete_user(remove_sounds=True)
            messages.add_message(request, messages.INFO,
                                 'Soft deleted user \'%s\' including her sounds. Comments and other content '
                                 'will appear under \'%s\' account' % (username, obj.username))
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))
        info = obj.profile.get_info_before_delete_user(remove_sounds=True)
        model_count = {model._meta.verbose_name_plural: len(objs) for model,
                objs in info['deleted'].model_objs.items()}
        tvars = {}
        tvars['model_count'] = dict(model_count).items()
        tvars['logic_deleted'] = info['logic_deleted']
        tvars['anonymised'] = info['anonymised']
        return render(request, 'accounts/delete_confirmation.html', tvars)

    delete_include_sounds.label = "Soft delete user (delete sounds)"
    delete_include_sounds.short_description = disable_active_user.short_description

    def delete_preserve_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            obj.profile.delete_user(remove_sounds=False)
            messages.add_message(request, messages.INFO,
                                 'Soft deleted user \'%s\' including her sounds. Comments and other content '
                                 'will appear under \'%s\' account' % (username, obj.username))
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        info = obj.profile.get_info_before_delete_user(remove_sounds=False)
        tvars = {}
        tvars['anonymised'] = info['anonymised']
        return render(request, 'accounts/delete_confirmation.html', tvars)
    delete_preserve_sounds.label = "Soft delete user (preserve sounds)"
    delete_preserve_sounds.short_description = disable_active_user_preserve_sounds.short_description

    change_actions = ('full_delete', 'delete_include_sounds', 'delete_preserve_sounds', )

admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)
