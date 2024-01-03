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

import logging

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from accounts.forms import username_taken_by_other_user
from accounts.models import Profile, UserFlag, EmailPreferenceType, OldUsername, DeletedUser, UserDeletionRequest, EmailBounce, GdprAcceptance
from general import tasks
from utils.admin_helpers import LargeTablePaginator

web_logger = logging.getLogger("web")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    readonly_fields = ('user',)
    raw_id_fields = ('geotag',)
    list_display = ('user', 'home_page', 'signature', 'is_whitelisted')
    ordering = ('id',)
    list_filter = ('is_whitelisted',)
    search_fields = ('=user__username',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserFlag)
class UserFlagAdmin(admin.ModelAdmin):
    readonly_fields = ('reporting_user', 'content_type', 'object_id', 'user')
    list_display = ('reporting_user', 'content_type', 'object_id', 'user')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DeletedUser)
class DeletedUserAdmin(admin.ModelAdmin):
    list_filter = ('reason',)
    readonly_fields = ('user', 'username', 'email', 'date_joined', 'last_login', 'deletion_date', 'reason')
    list_display = ('get_object_link', 'get_view_link', 'deletion_date', 'reason')
    search_fields = ('=username',)

    @admin.display(
        description='DeletedUser',
        ordering='username',
    )
    def get_object_link(self, obj):
        return mark_safe(
            '<a href="{}" target="_blank">{}</a>'.format(
                reverse('admin:accounts_deleteduser_change', args=[obj.id]), f'DeletedUser: {obj.username}'
            )
        )

    @admin.display(description='View on site')
    def get_view_link(self, obj):
        if obj.user is None:
            return '-'
        else:
            return mark_safe(
                '<a href="{}" target="_blank">{}</a>'.format(
                    reverse('account', args=[obj.user.username]), obj.user.username
                )
            )

    @admin.display(description='# sounds')
    def get_num_sounds(self, obj):
        return f'{obj.profile.num_sounds}'


class AdminUserForm(UserChangeForm):

    def clean_username(self):
        username = self.cleaned_data["username"]
        # Check that username is not taken by another user (or was not used in the past by another user or by a user
        # that was deleted).
        # NOTE: as opposed as in accounts.forms.ProfileForm, here we don't impose the limitation of changing the
        # username a maximum number of times.
        if username.lower() == self.instance.username.lower():
            return username
        if not username_taken_by_other_user(username):
            return username
        raise ValidationError(
            "This username is already taken or has been in used in the past by this or some other "
            "user."
        )

    def clean_email(self):
        # Check that email is not being used by another user (case insensitive)
        email = self.cleaned_data["email"]
        try:
            User.objects.exclude(pk=self.instance.id).get(email__iexact=email)
        except User.DoesNotExist:
            return email
        raise ValidationError("This email is already being used by another user.")


class FreesoundUserAdmin(DjangoObjectActions, UserAdmin):
    readonly_fields = ('last_login', 'date_joined')
    search_fields = ('=username', '=email')
    actions = ()
    list_display = ('username', 'email', 'get_num_sounds', 'get_num_posts', 'date_joined', 'get_view_link')
    list_filter = ()
    ordering = ('id',)
    show_full_result_count = False
    form = AdminUserForm
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal info', {
            'fields': ('email',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    paginator = LargeTablePaginator

    def get_queryset(self, request):
        # Override 'get_queryset' to optimize query by using select_related on appropriate fields
        qs = super().get_queryset(request)
        qs = qs.select_related('profile')
        return qs

    def has_delete_permission(self, request, obj=None):
        # Disable the "Delete" button in the user detail page
        # We want to disable that button in favour of the custom asynchronous delete change actions
        return False

    @admin.display(description='View on site')
    def get_view_link(self, obj):
        return mark_safe(
            '<a href="{}" target="_blank">{}</a>'.format(reverse('account', args=[obj.username]), obj.username)
        )

    @admin.display(description='# sounds')
    def get_num_sounds(self, obj):
        return f'{obj.profile.num_sounds}'

    @admin.display(description='# posts')
    def get_num_posts(self, obj):
        return f'{obj.profile.num_posts}'

    def get_actions(self, request):
        # Disable the "delete" action in the list
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    @admin.action(description="Delete the user but keep the sounds available")
    def delete_preserve_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            delete_action = tasks.DELETE_USER_KEEP_SOUNDS_ACTION_NAME
            delete_reason = DeletedUser.DELETION_REASON_DELETED_BY_ADMIN
            web_logger.info(f'Requested async deletion of user {obj.id} - {delete_action}')

            # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
            UserDeletionRequest.objects.create(
                user_from=request.user,
                user_to=obj,
                status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                triggered_deletion_action=delete_action,
                triggered_deletion_reason=delete_reason
            )

            # Trigger async task so user gets deleted asynchronously
            tasks.delete_user.delay(user_id=obj.id, deletion_action=delete_action, deletion_reason=delete_reason)

            # Show message to admin user
            messages.add_message(
                request, messages.INFO,
                'User \'%s\' will be deleted asynchronously. Sounds, comments and other related '
                'user content will still be available but appear under anonymised account' % username
            )
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=False, include_other_related_objects=False)

        tvars = {'users_to_delete': [], 'type': 'delete_preserve_sounds'}
        tvars['users_to_delete'].append(user_info)
        return render(request, 'accounts/admin_delete_confirmation.html', tvars)

    delete_preserve_sounds.label = "Delete user only"

    @admin.action(description="Delete the user and the sounds")
    def delete_include_sounds(self, request, obj):
        username = obj.username
        if request.method == "POST":
            delete_action = tasks.DELETE_USER_DELETE_SOUNDS_ACTION_NAME
            delete_reason = DeletedUser.DELETION_REASON_DELETED_BY_ADMIN
            web_logger.info(f'Requested async deletion of user {obj.id} - {delete_action}')

            # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
            UserDeletionRequest.objects.create(
                user_from=request.user,
                user_to=obj,
                status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                triggered_deletion_action=delete_action,
                triggered_deletion_reason=delete_reason
            )

            # Trigger async task so user gets deleted asynchronously
            tasks.delete_user.delay(user_id=obj.id, deletion_action=delete_action, deletion_reason=delete_reason)

            # Show message to admin user
            messages.add_message(
                request, messages.INFO, 'User \'%s\' will be deleted asynchronously. Sounds will be deleted as well. '
                'Comments and other related user content will still be available but appear under '
                'anonymised account' % username
            )
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=False)
        user_info['deleted_objects_details'] = {}
        model_count = {
            model._meta.verbose_name_plural: len(objs) for model, objs in user_info['deleted'].model_objs.items()
        }
        user_info['deleted_objects_details']['model_count'] = list(dict(model_count).items())

        tvars = {'users_to_delete': [], 'type': 'delete_include_sounds'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/admin_delete_confirmation.html', tvars)

    delete_include_sounds.label = "Delete user and sounds"

    @admin.action(description="Delete the user and the sounds, mark deleted user as spammer")
    def delete_spammer(self, request, obj):
        username = obj.username
        if request.method == "POST":
            delete_action = tasks.DELETE_SPAMMER_USER_ACTION_NAME
            delete_reason = DeletedUser.DELETION_REASON_SPAMMER
            web_logger.info(f'Requested async deletion of user {obj.id} - {delete_action}')

            # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
            UserDeletionRequest.objects.create(
                user_from=request.user,
                user_to=obj,
                status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                triggered_deletion_action=delete_action,
                triggered_deletion_reason=delete_reason
            )

            # Trigger async task so user gets deleted asynchronously
            tasks.delete_user.delay(user_id=obj.id, deletion_action=delete_action, deletion_reason=delete_reason)

            # Show message to admin user
            messages.add_message(
                request, messages.INFO,
                'User \'%s\' will be deleted asynchronously including sounds and all of its related '
                'content.' % username
            )
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=True)
        user_info['deleted_objects_details'] = {}
        model_count = {
            model._meta.verbose_name_plural: len(objs) for model, objs in user_info['deleted'].model_objs.items()
        }
        user_info['deleted_objects_details']['model_count'] = list(dict(model_count).items())

        tvars = {'users_to_delete': [], 'type': 'delete_spammer'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/admin_delete_confirmation.html', tvars)

    delete_spammer.label = "Delete as spammer"

    @admin.action(description='Completely delete user from db')
    def full_delete(self, request, obj):
        username = obj.username
        if request.method == "POST":
            delete_action = tasks.FULL_DELETE_USER_ACTION_NAME
            delete_reason = DeletedUser.DELETION_REASON_DELETED_BY_ADMIN
            web_logger.info(f'Requested async deletion of user {obj.id} - {delete_action}')

            # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
            UserDeletionRequest.objects.create(
                user_from=request.user,
                user_to=obj,
                status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                triggered_deletion_action=delete_action,
                triggered_deletion_reason=delete_reason
            )

            # Trigger async task so user gets deleted asynchronously
            tasks.delete_user.delay(user_id=obj.id, deletion_action=delete_action, deletion_reason=delete_reason)

            # Show message to admin user
            messages.add_message(
                request, messages.INFO,
                'User \'%s\' will be deleted asynchronously including sounds and all of its related'
                'content.' % username
            )
            return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

        user_info = obj.profile.get_info_before_delete_user(include_sounds=True, include_other_related_objects=True)
        user_info['deleted_objects_details'] = {}
        model_count = {
            model._meta.verbose_name_plural: len(objs) for model, objs in user_info['deleted'].model_objs.items()
        }
        user_info['deleted_objects_details']['model_count'] = list(dict(model_count).items())

        tvars = {'users_to_delete': [], 'type': 'full_delete'}
        tvars['users_to_delete'].append(user_info)

        return render(request, 'accounts/admin_delete_confirmation.html', tvars)

    full_delete.label = "Full delete"

    @admin.action(description='Clear all user flags for of spam reports and akismet')
    def clear_spam_flags(self, request, obj):
        num_akismet, _ = obj.akismetspam_set.all().delete()
        num_reports, _ = obj.flags.all().delete()
        messages.add_message(
            request, messages.INFO, 'User \'%s\' flags have been cleared: %i akismet flags and %i user reports.' %
            (obj.username, num_akismet, num_reports)
        )
        return HttpResponseRedirect(reverse('admin:auth_user_change', args=[obj.id]))

    clear_spam_flags.label = "Clear spam flags"

    @admin.action(description='Open user on site')
    def view_on_site_action(self, request, obj):
        return HttpResponseRedirect(reverse('account', args=[obj.username]))

    view_on_site_action.label = "View on site"

    @admin.action(description='Edit profile in admin')
    def edit_profile_admin(self, request, obj):
        return HttpResponseRedirect(reverse('admin:accounts_profile_change', args=[obj.profile.id]))

    edit_profile_admin.label = "Edit profile in admin"

    # NOTE: in the line below we removed the 'full_delete' option as ideally we should never need to use it. In for
    # some unexpected reason we happen to need it, we can call the .delete() method on a user object using the terminal.
    # If we observe a real need for that, we can re-add the option to the admin.
    change_actions = (
        'edit_profile_admin',
        'view_on_site_action',
        'clear_spam_flags',
        'delete_spammer',
        'delete_include_sounds',
        'delete_preserve_sounds',
    )


@admin.register(OldUsername)
class OldUsernameAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'username')
    search_fields = ('=username',)
    list_display = ('user', 'username')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserDeletionRequest)
class UserDeletionRequestAdmin(admin.ModelAdmin):
    list_filter = ('status',)
    search_fields = ('=username_to', '=email_from')
    raw_id_fields = ('user_from', 'user_to')
    list_display = (
        'status', 'email_from', 'username_from', 'username_to', 'user_to_link', 'deleted_user_link', 'get_reason',
        'last_updated'
    )
    fieldsets = ((
        None, {
            'fields':
                ('status', 'email_from', 'user_to', 'username_to', 'deleted_user', 'status_history', 'last_updated')
        }
    ),)
    readonly_fields = ('status_history', 'user_from', 'username_from', 'username_to', 'last_updated', 'deleted_user')

    def get_queryset(self, request):
        # Override 'get_queryset' to optimize query by using select_related on appropriate fields
        qs = super().get_queryset(request)
        qs = qs.select_related('user_from', 'deleted_user', 'user_to')
        return qs

    @admin.display(
        description='DeletedUser',
        ordering='deleted_user',
    )
    def deleted_user_link(self, obj):
        if obj.deleted_user is None:
            return '-'
        return mark_safe(
            '<a href="{}" target="_blank">{}</a>'.format(
                reverse('admin:accounts_deleteduser_change', args=[obj.deleted_user_id]),
                f'DeletedUser: {obj.deleted_user.username}'
            )
        )

    @admin.display(
        description='User to',
        ordering='user_to',
    )
    def user_to_link(self, obj):
        if obj.user_to is None:
            return '-'
        return mark_safe(
            '<a href="{}" target="_blank">{}</a>'.format(
                reverse('admin:auth_user_change', args=[obj.user_to_id]), obj.user_to.username
            )
        )

    @admin.display(description='Reason')
    def get_reason(self, obj):
        if obj.triggered_deletion_reason:
            return [
                label for key, label in DeletedUser.DELETION_REASON_CHOICES if key == obj.triggered_deletion_reason
            ][0]
        else:
            return '-'


@admin.register(EmailBounce)
class EmailBounceAdmin(admin.ModelAdmin):
    search_fields = ('=user__username',)
    list_display = ('user', 'type', 'timestamp')
    readonly_fields = ('user', 'type', 'timestamp')


admin.site.unregister(User)
admin.site.register(User, FreesoundUserAdmin)
admin.site.register(EmailPreferenceType)
