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

import json

import gearman
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django_object_actions import DjangoObjectActions

from accounts.models import Profile, UserFlag, EmailPreferenceType


def disable_active_user(modeladmin, request, queryset):
    if request.POST.get('confirmation', False):
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        for user in queryset:
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id':user.id, 'action': "delete_user_delete_sounds"}),
                wait_until_complete=False, background=True)
        messages.add_message(request, messages.INFO,
             '%d users will be soft deleted asynchronously, related sound are '
             'going to be deleted as well' % (queryset.count()))
        return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

    params = [(k,v) for k in request.POST.keys() for v in request.POST.getlist(k)]
    tvars = {'anonymised': [], 'params': params}
    for obj in queryset:

        info = obj.profile.get_info_before_delete_user(remove_sounds=True)
        model_count = {model._meta.verbose_name_plural: len(objs) for model,
                objs in info['deleted'].model_objs.items()}
        anon = {'anonymised': []}
        anon['model_count'] = dict(model_count).items()
        anon['logic_deleted'] = info['logic_deleted']
        anon['name'] = info['anonymised']
        tvars['anonymised'].append(anon)

    return render(request, 'accounts/delete_confirmation.html', tvars)

disable_active_user.short_description = "'Soft' delete selected users, preserve posts, threads and comments (delete sounds)"


def disable_active_user_preserve_sounds(modeladmin, request, queryset):
    if request.POST.get('confirmation', False):
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        for user in queryset:
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id':user.id, 'action': "delete_user_keep_sounds"}),
                wait_until_complete=False, background=True)
        messages.add_message(request, messages.INFO,
             '%d users will be soft deleted asynchronously' % (queryset.count()))
        return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

    params = [(k,v) for k in request.POST.keys() for v in request.POST.getlist(k)]
    tvars = {'anonymised': [], 'params': params}
    for obj in queryset:
        info = obj.profile.get_info_before_delete_user(remove_sounds=False)
        tvars['anonymised'].append({'name': info['anonymised']})
    return render(request, 'accounts/delete_confirmation.html', tvars)

disable_active_user_preserve_sounds.short_description = "'Soft' delete selected users, preserve sounds and everything else"


class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'geotag')
    list_display = ('user', 'home_page', 'signature', 'is_whitelisted')
    ordering = ('id', )
    list_filter = ('is_whitelisted', )
    search_fields = ('=user__username', )

admin.site.register(Profile, ProfileAdmin)


class UserFlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'reporting_user', 'content_type')
    list_display = ('user', 'reporting_user', 'content_type')

admin.site.register(UserFlag, UserFlagAdmin)


class FreesoundUserAdmin(DjangoObjectActions, UserAdmin):
    search_fields = ('=username', '=email')
    actions = (disable_active_user, disable_active_user_preserve_sounds, )
    list_display = ('username', 'email')
    list_filter = ()
    ordering = ('id', )
    show_full_result_count = False

    def full_delete(self, request, obj):
        username = obj.username
        if request.method == "POST":
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id': obj.id, 'action': "full_delete_user"}),
                wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be fully deleted '
                                 'asynchronously from the database' % (username))
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        info = obj.profile.get_info_before_delete_user(remove_sounds=False,
                remove_user=True)
        model_count = {model._meta.verbose_name_plural: len(objs) for model,
                objs in info['deleted'].model_objs.items()}
        tvars = {'anonymised': []}
        anon = {}
        anon['model_count'] = dict(model_count).items()
        anon['name'] = info['anonymised']
        anon['deleted'] = True
        tvars['anonymised'].append(anon)
        return render(request, 'accounts/delete_confirmation.html', tvars)
    full_delete.label = "Full delete user"
    full_delete.short_description = 'Completely delete user from db'

    def delete_include_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id': obj.id, 'action': "delete_user_delete_sounds"}),
                wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be soft deleted'
                                 ' asynchronously. Sounds and other related'
                                 ' content will be deleted.' % (username))
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))
        info = obj.profile.get_info_before_delete_user(remove_sounds=True)
        model_count = {model._meta.verbose_name_plural: len(objs) for model,
                objs in info['deleted'].model_objs.items()}
        tvars = {'anonymised': []}
        anon = {}
        anon['model_count'] = dict(model_count).items()
        anon['logic_deleted'] = info['logic_deleted']
        anon['name'] = info['anonymised']
        tvars['anonymised'].append(anon)
        return render(request, 'accounts/delete_confirmation.html', tvars)

    delete_include_sounds.label = "Soft delete user (delete sounds)"
    delete_include_sounds.short_description = disable_active_user.short_description

    def delete_preserve_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id': obj.id, 'action': "delete_user_keep_sounds"}),
                wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be soft deleted asynchronously. Comments and other content '
                                 'will appear under anonymised account' % (username))
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        info = obj.profile.get_info_before_delete_user(remove_sounds=False)
        tvars = {'anonymised': []}
        tvars['anonymised'].append({'name': info['anonymised']})
        return render(request, 'accounts/delete_confirmation.html', tvars)
    delete_preserve_sounds.label = "Soft delete user (preserve sounds)"
    delete_preserve_sounds.short_description = disable_active_user_preserve_sounds.short_description

    change_actions = ('full_delete', 'delete_include_sounds', 'delete_preserve_sounds', )

admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)

admin.site.register(EmailPreferenceType)
