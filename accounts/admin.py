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
import logging

import gearman
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import connection
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.functional import cached_property
from django_object_actions import DjangoObjectActions

from accounts.models import Profile, UserFlag, EmailPreferenceType, OldUsername, DeletedUser, UserGDPRDeletionRequest, EmailBounce

DELETE_SPAMMER_USER_ACTION_NAME = 'delete_user_spammer'
FULL_DELETE_USER_ACTION_NAME = 'full_delete_user'
DELETE_USER_DELETE_SOUNDS_ACTION_NAME = 'delete_user_delete_sounds'
DELETE_USER_KEEP_SOUNDS_ACTION_NAME = 'delete_user_keep_sounds'

web_logger = logging.getLogger("web")


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


class LargeTablePaginator(Paginator):
    """ We use the information on postgres table 'reltuples' to avoid using count(*) for performance. """
    @cached_property
    def count(self):
        try:
            if not self.object_list.query.where:
                cursor = connection.cursor()
                cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s",
                    [self.object_list.query.model._meta.db_table])
                ret = int(cursor.fetchone()[0])
                return ret
            else :
                return self.object_list.count()
        except :
            # AttributeError if object_list has no count() method.
            return len(self.object_list)


class AdminUserForm(UserChangeForm):

    def clean_username(self):
        username = self.cleaned_data["username"]
        # Check that:
        #   1) It is not taken by another user
        #   2) It was not used in the past by another (or the same) user
        # NOTE: as opposed as in accounts.forms.ProfileForm, here we don't impose the limitation of changing the
        # username a maximum number of times.
        try:
            User.objects.exclude(pk=self.instance.id).get(username__iexact=username)
        except User.DoesNotExist:
            try:
                OldUsername.objects.get(username__iexact=username)
            except OldUsername.DoesNotExist:
                return username
        raise ValidationError("This username is already taken or has been in used in the past by this or some other "
                              "user.")


class FreesoundUserAdmin(DjangoObjectActions, UserAdmin):
    search_fields = ('=username', '=email')
    actions = ()
    list_display = ('username', 'email')
    list_filter = ()
    ordering = ('id', )
    show_full_result_count = False
    form = AdminUserForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', )}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
     )

    paginator = LargeTablePaginator

    def has_delete_permission(self, request, obj=None):
        # Disable the "Delete" button in the user detail page
        # We want to disable that button in favour of the custom asynchronous delete change actions
        return False

    def get_actions(self, request):
        # Disable the "delete" action in the list
        actions = super(FreesoundUserAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def delete_preserve_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            web_logger.info('Requested async deletion of user {0} - {1}'.format(obj.id,
                                                                                DELETE_USER_KEEP_SOUNDS_ACTION_NAME))
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                    json.dumps({'user_id': obj.id, 'action': DELETE_USER_KEEP_SOUNDS_ACTION_NAME}),
                wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be deleted asynchronously. Sounds, comments and other related '
                                 'user content will still be available but appear under anonymised account' % username)
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=False, include_other_related_objects=False)

        tvars = {'users_to_delete': [], 'type': 'delete_preserve_sounds'}
        tvars['users_to_delete'].append(user_info)
        return render(request, 'accounts/delete_confirmation.html', tvars)

    delete_preserve_sounds.label = "Delete user only"
    delete_preserve_sounds.short_description = "Delete the user but keep the sounds available"

    def delete_include_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            web_logger.info('Requested async deletion of user {0} - {1}'.format(obj.id,
                                                                                DELETE_USER_DELETE_SOUNDS_ACTION_NAME))
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                                 json.dumps({'user_id': obj.id, 'action': DELETE_USER_DELETE_SOUNDS_ACTION_NAME}),
                                 wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be deleted asynchronously. Sounds will be deleted as well. '
                                 'Comments and other related user content will still be available but appear under '
                                 'anonymised account' % username)
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=False)
        user_info['deleted_objects_details'] = {}
        model_count = {model._meta.verbose_name_plural: len(objs) for
                       model, objs in user_info['deleted'].model_objs.items()}
        user_info['deleted_objects_details']['model_count'] = dict(model_count).items()
        user_info['deleted_objects_details']['logic_deleted'] = user_info['logic_deleted']

        tvars = {'users_to_delete': [], 'type': 'delete_include_sounds'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/delete_confirmation.html', tvars)

    delete_include_sounds.label = "Delete user and sounds"
    delete_include_sounds.short_description = "Delete the user and the sounds"

    def delete_spammer(self, request, obj):
        username = obj.username
        if request.method == "POST":
            web_logger.info('Requested async deletion of user {0} - {1}'.format(obj.id,
                                                                                DELETE_SPAMMER_USER_ACTION_NAME))
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                                 json.dumps({'user_id': obj.id, 'action': DELETE_SPAMMER_USER_ACTION_NAME}),
                                 wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be deleted asynchronously including sounds and all of its related'
                                 'content.' % username)
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=True)
        user_info['deleted_objects_details'] = {}
        model_count = {model._meta.verbose_name_plural: len(objs) for
                       model, objs in user_info['deleted'].model_objs.items()}
        user_info['deleted_objects_details']['model_count'] = dict(model_count).items()
        user_info['deleted_objects_details']['logic_deleted'] = user_info['logic_deleted']

        tvars = {'users_to_delete': [], 'type': 'delete_spammer'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/delete_confirmation.html', tvars)

    delete_spammer.label = "Delete spammer"
    delete_spammer.short_description = "Delete the user and the sounds, mark deleted user as spammer"

    def full_delete(self, request, obj):
        username = obj.username
        if request.method == "POST":
            web_logger.info('Requested async deletion of user {0} - {1}'.format(obj.id,
                                                                                FULL_DELETE_USER_ACTION_NAME))
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                                 json.dumps({'user_id': obj.id, 'action': FULL_DELETE_USER_ACTION_NAME}),
                                 wait_until_complete=False, background=True)
            messages.add_message(request, messages.INFO,
                                 'User \'%s\' will be deleted asynchronously including sounds and all of its related'
                                 'content.' % username)
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=True)
        user_info['deleted_objects_details'] = {}
        model_count = {model._meta.verbose_name_plural: len(objs) for
                       model, objs in user_info['deleted'].model_objs.items()}
        user_info['deleted_objects_details']['model_count'] = dict(model_count).items()
        user_info['deleted_objects_details']['logic_deleted'] = user_info['logic_deleted']

        tvars = {'users_to_delete': [], 'type': 'full_delete'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/delete_confirmation.html', tvars)

    full_delete.label = "Full delete"
    full_delete.short_description = 'Completely delete user from db'

    change_actions = ('delete_spammer', 'delete_include_sounds', 'delete_preserve_sounds',  'full_delete', )


class OldUsernameAdmin(admin.ModelAdmin):
    search_fields = ('=username', )
    raw_id_fields = ('user', )
    list_display = ('user', 'username')


class UserGDPRDeletionRequestAdmin(admin.ModelAdmin):
    search_fields = ('=username', '=email')
    raw_id_fields = ('user', )
    list_display = ('email', 'username', 'user_link', 'deleted_user_link', 'status')
    list_filter = ('status', )
    fieldsets = (
        (None, {'fields': ('email', 'status', 'user', 'username')}),
    )

    def get_queryset(self, request):
        # overrride 'get_queryset' to optimize query by using select_related on 'user' and 'deleted_user'
        qs = super(UserGDPRDeletionRequestAdmin, self).get_queryset(request)
        qs = qs.select_related('user', 'deleted_user')
        return qs

    def user_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('admin:auth_user_change', args=[obj.user_id]),
                                                              obj.user.username)
    user_link.allow_tags = True
    user_link.admin_order_field = 'user'
    user_link.short_description = 'User object'

    def deleted_user_link(self, obj):
        if obj.deleted_user is None:
            return '-'
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('admin:accounts_deleteduser_change', args=[obj.deleted_user_id]),
                                                              obj.deleted_user.username)
    deleted_user_link.allow_tags = True
    deleted_user_link.admin_order_field = 'deleted_user'
    deleted_user_link.short_description = 'Deleted user object'


class DeletedUserAdmin(admin.ModelAdmin):
    readonly_fields = ['user']


class EmailBounceAdmin(admin.ModelAdmin):
    search_fields = ('=user__username',)
    list_display = ('user', )


admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)
admin.site.register(EmailBounce, EmailBounceAdmin)
admin.site.register(EmailPreferenceType)
admin.site.register(OldUsername, OldUsernameAdmin)
admin.site.register(DeletedUser, DeletedUserAdmin)
admin.site.register(UserGDPRDeletionRequest, UserGDPRDeletionRequestAdmin)

