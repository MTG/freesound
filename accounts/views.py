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

import io
import csv
import datetime
import errno
import json
import logging
import os
import tempfile
import time
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, PasswordResetCompleteView, PasswordResetConfirmView, \
    PasswordChangeView, PasswordChangeDoneView
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.db.models.expressions import Value
from django.db.models.fields import CharField
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, Http404, \
    HttpResponsePermanentRedirect, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import base36_to_int
from django.utils.http import int_to_base36
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from general.templatetags.absurl import url2absurl
from oauth2_provider.models import AccessToken

import tickets.views as TicketViews
import utils.sound_upload
from general.tasks import DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from accounts.forms import EmailResetForm, FsPasswordResetForm, FsSetPasswordForm, \
    UploadFileForm, FlashUploadFileForm, FileChoiceForm, RegistrationForm, \
    ProfileForm, AvatarForm, TermsOfServiceForm, DeleteUserForm, EmailSettingsForm, BulkDescribeForm, \
    UsernameField, ProblemsLoggingInForm, username_taken_by_other_user, FsPasswordChangeForm
from general.templatetags.util import license_with_version
from accounts.models import Profile, ResetEmailRequest, UserFlag, DeletedUser, UserDeletionRequest
from bookmarks.models import Bookmark
from comments.models import Comment
from follow import follow_utils
from forum.models import Post
from general import tasks
from messages.models import Message
from sounds.forms import LicenseForm, PackForm
from sounds.models import Sound, Pack, Download, SoundLicenseHistory, BulkUploadProgress, PackDownload
from sounds.views import edit_and_describe_sounds_helper
from tickets.models import TicketComment, Ticket, UserAnnotation
from utils.cache import invalidate_user_template_caches
from utils.dbtime import DBTime
from utils.filesystem import generate_tree, remove_directory_if_empty
from utils.images import extract_square
from utils.logging_filters import get_client_ip
from utils.mail import send_mail_template, send_mail_template_to_support
from utils.mirror_files import copy_avatar_to_mirror_locations, \
    copy_uploaded_file_to_mirror_locations, remove_uploaded_file_from_mirror_locations, \
    remove_empty_user_directory_from_mirror_locations
from utils.onlineusers import get_online_users
from utils.pagination import paginate
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted

sounds_logger = logging.getLogger('sounds')
upload_logger = logging.getLogger('file_upload')
web_logger = logging.getLogger('web')
volatile_logger = logging.getLogger('volatile')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def crash_me(request):
    raise Exception


def ratelimited_error(request, exception):
    if 'similar' in request.path:
        path = '/people/<username>/sounds/<sound_id>/similar/'
    else:
        path = request.path
    if not path.endswith('/'):
        path += '/'
    volatile_logger.info(f"Rate limited IP ({json.dumps({'ip': get_client_ip(request), 'path': path})})")
    return render(request, '429.html', status=429)


def login(request, template_name, authentication_form):
    # Freesound-specific login view to check if a user has multiple accounts
    # with the same email address. We can switch back to the regular django view
    # once all accounts are adapted
    response = LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=authentication_form)(request)
    if isinstance(response, HttpResponseRedirect):
        # If there is a redirect it's because the login was successful
        # Now we check if the logged in user has shared email problems
        if request.user.profile.has_shared_email():
            # If the logged in user has an email shared with other accounts, we redirect to the email update page
            redirect_url = reverse("accounts-multi-email-cleanup")
            next_param = request.POST.get('next', None)
            if next_param:
                redirect_url += f'?next={next_param}'
            return HttpResponseRedirect(redirect_url)
        else:
            return response

    return response


def password_reset_confirm(request, uidb64, token):
    """
    Password reset = change password without user being logged in (classic "forgot password" feature).
    This view is called after user has received an email with instructions for resetting the password and clicks the
    reset link.

    We set 'next_path'  parameter so we configure login modal to redirect to front page after successful login
    instead of staying in PasswordResetCompleteView (the current path).
    """
    response = PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=FsSetPasswordForm,
        extra_context={'next_path': reverse('accounts-home')}
    )(request, uidb64=uidb64, token=token)
    return response


def password_reset_complete(request):
    """
    Password reset = change password without user being logged in (classic "forgot password" feature).
    This view is called when the password has been reset successfully.

    We set 'next_path'  parameter so we configure login modal to redirect to front page after successful login
    instead of staying in PasswordResetCompleteView (the current path).
    """
    response = PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
        extra_context={'next_path': reverse('accounts-home')})(request)
    return response


def password_change_form(request):
    """
    Password change = change password from the account settings page, while user is logged in.
    This view is called when user requests to change the password and contains the form to do so.
    """
    response = PasswordChangeView.as_view(
        form_class=FsPasswordChangeForm,
        template_name='accounts/password_change_form.html',
        extra_context={'activePage': 'password'})(request)
    return response


def password_change_done(request):
    """
    Password change = change password from the account settings page, while user is logged in.
    This view is called when user has successfully changed the password by filling in the password change form.
    """
    response = PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html',
        extra_context={'activePage': 'password'})(request)
    return response


@login_required
@transaction.atomic()
def multi_email_cleanup(request):

    # If user does not have shared email problems, then it should have not visited this page
    if not request.user.profile.has_shared_email():
        return HttpResponseRedirect(reverse('accounts-home'))

    # Check if shared email problems have been fixed (if user changed one of the two emails)
    same_user = request.user.profile.get_sameuser_object()
    email_issues_still_valid = True

    if same_user.main_user_changed_email():
        # Then assign original email to secondary user (if user didn't change it)
        if not same_user.secondary_user_changed_email():
            same_user.secondary_user.email = same_user.orig_email
            same_user.secondary_user.save()
        email_issues_still_valid = False

    if same_user.secondary_user_changed_email():
        # Then the email problems have been fixeed when email of secondary user was changed
        # No need to re-assign emails here
        email_issues_still_valid = False

    if not email_issues_still_valid:
        # If problems have been fixed, remove same_user object to users are not redirected here again
        same_user.delete()

        # Redirect to where the user was going (in this way this whole process will have been transparent)
        return HttpResponseRedirect(request.GET.get('next', reverse('accounts-home')))
    else:
        # If email issues are still valid, then we show the email cleanup page with the instructions
        return render(request, 'accounts/multi_email_cleanup.html', {
            'same_user': same_user, 'next': request.GET.get('next', reverse('accounts-home'))})


def check_username(request):
    """AJAX endpoint to check if a specified username is available to be registered.
    This checks against the normal username validator, and then also verifies to see
    if the username already exists in the database.

    Returns JSON {'result': true} if the username is valid and can be used"""
    username = request.GET.get('username', None)
    username_valid = False
    username_field = UsernameField()
    if username:
        try:
            username_field.run_validators(username)
            # If the validator passes, check if the username is indeed available
            username_valid = not username_taken_by_other_user(username)
        except ValidationError:
            username_valid = False

    return JsonResponse({'result': username_valid})


@login_required
@transaction.atomic()
def bulk_license_change(request):
    if request.method == 'POST':
        form = LicenseForm(request.POST, hide_old_license_versions=True)
        if form.is_valid():
            selected_license = form.cleaned_data['license']
            Sound.objects.filter(user=request.user).update(license=selected_license, is_index_dirty=True)
            for sound in Sound.objects.filter(user=request.user).all():
                SoundLicenseHistory.objects.create(sound=sound, license=selected_license)
            request.user.profile.has_old_license = False
            request.user.profile.save()
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = LicenseForm(hide_old_license_versions=True)
    tvars = {'form': form}
    return render(request, 'accounts/choose_new_license.html', tvars)


@login_required
def tos_acceptance(request):
    has_sounds_with_old_cc_licenses = request.user.profile.has_sounds_with_old_cc_licenses()
    if request.method == 'POST':
        form = TermsOfServiceForm(request.POST)
        if form.is_valid():
            profile = request.user.profile
            profile.agree_to_gdpr()

            if form.cleaned_data['accepted_license_change']:
                profile.upgrade_old_cc_licenses_to_new_cc_licenses()

            if form.cleaned_data['next']:
                return HttpResponseRedirect(form.cleaned_data['next'])
            else:
                return HttpResponseRedirect(reverse('accounts-home'))
    else:
        next_param = request.GET.get('next')
        form = TermsOfServiceForm(initial={'next': next_param})
    tvars = {'form': form, 'has_sounds_with_old_cc_licenses': has_sounds_with_old_cc_licenses}
    return render(request, 'accounts/gdpr_consent.html', tvars)


@login_required
def update_old_cc_licenses(request):
    request.user.profile.upgrade_old_cc_licenses_to_new_cc_licenses()
    next = request.GET.get('next', None)
    if next is not None:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse('accounts-home'))


@transaction.atomic()
def registration_modal(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_activation(user)
            # If the form is valid we will return a JSON response with the URL where
            # the user should be redirected (a URL which will include the "Almost done" message). The browser
            # will then take this URL and redirect the user.
            next_param = request.GET.get('next', None)
            if next_param is not None:
                return JsonResponse({'redirectURL': next_param + '?feedbackRegistration=1' if '?' not in next_param \
                                    else next_param + '&feedbackRegistration=1'})
            else:
                return JsonResponse({'redirectURL': reverse('front-page') + '?feedbackRegistration=1'})
        else:
            # If the form is NOT valid we return the Django rendered HTML version of the
            # registration modal (which includes the form and error messages) so the browser can show the updated
            # modal contents to the user
            return render(request, 'accounts/modal_registration.html', {'registration_form': form})
    else:
        form = RegistrationForm()

    return render(request, 'accounts/modal_registration.html', {'registration_form': form})


def activate_user(request, username, uid_hash):
    # NOTE: in these views we set "next_path" variable so we make sure that if the
    # login modal is used the user will be redirected to the front-page instead of that same page

    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return render(request, 'accounts/activate.html', {'user_does_not_exist': True,
                                                          'next_path': reverse('accounts-home')})

    if not default_token_generator.check_token(user, uid_hash):
        return render(request, 'accounts/activate.html', {'decode_error': True,
                                                          'next_path': reverse('accounts-home')})

    user.is_active = True
    user.save()
    return render(request, 'accounts/activate.html', {'all_ok': True, 'next_path': reverse('accounts-home')})


def send_activation(user):
    token = default_token_generator.make_token(user)
    username = user.username
    tvars = {
        'user': user,
        'username': username,
        'hash': token
    }
    send_mail_template(settings.EMAIL_SUBJECT_ACTIVATION_LINK, 'emails/email_activation.txt', tvars, user_to=user)


def resend_activation(request):
    return HttpResponseRedirect(reverse('front-page') + '?loginProblems=1')


def username_reminder(request):
    return HttpResponseRedirect(reverse('front-page') + '?loginProblems=1')
    

@login_required
def home(request):
    # In BW we no longer have the concept of "home", thus we redirect to the account page
    # This view is however still useful as we can redirect to the account page of the request.user
    # uing the path /home/ without needing to construct the URL with the username in it
    return HttpResponseRedirect(reverse('account', args=[request.user.username]))


@login_required
def edit_email_settings(request):
    if request.method == "POST":
        form = EmailSettingsForm(request.POST)
        if form.is_valid():
            email_type_ids = form.cleaned_data['email_types']
            request.user.profile.set_enabled_email_types(email_type_ids)
            messages.add_message(request, messages.INFO, 'Your email notification preferences have been updated')
    else:
        # Get list of enabled email_types
        all_emails = request.user.profile.get_enabled_email_types()
        form = EmailSettingsForm(initial={
            'email_types': all_emails,
            })
    tvars = {
        'form': form,
        'activePage': 'notifications'
    }
    return render(request, 'accounts/edit_email_settings.html', tvars)


@login_required
@transaction.atomic()
def edit(request):
    profile = request.user.profile

    def is_selected(prefix):
        if request.method == "POST":
            for name in request.POST.keys():
                if name.startswith(prefix + '-'):
                    return True
            if request.FILES:
                for name in request.FILES.keys():
                    if name.startswith(prefix + '-'):
                        return True
        return False

    if is_selected("profile"):
        profile_form = ProfileForm(request, request.POST, instance=profile, prefix="profile")
        old_sound_signature = profile.sound_signature
        if profile_form.is_valid():
            # Update username, this will create an entry in OldUsername
            request.user.username = profile_form.cleaned_data['username']
            request.user.save()
            invalidate_user_template_caches(request.user.id)
            profile.save()
            msg_txt = "Your profile has been updated correctly."
            if old_sound_signature != profile.sound_signature:
                msg_txt += " Please note that it might take some time until your sound signature is updated in all your sounds."
            messages.add_message(request, messages.INFO, msg_txt)
            return HttpResponseRedirect(reverse("accounts-edit"))
    else:
        profile_form = ProfileForm(request, instance=profile, prefix="profile")

    if is_selected("image"):
        image_form = AvatarForm(request.POST, request.FILES, prefix="image")
        if image_form.is_valid():
            if image_form.cleaned_data["remove"]:
                profile.has_avatar = False
                profile.save()
            else:
                handle_uploaded_image(profile, image_form.cleaned_data["file"])
                profile.has_avatar = True
                profile.save()
            invalidate_user_template_caches(request.user.id)
            msg_txt = "Your profile has been updated correctly."
            messages.add_message(request, messages.INFO, msg_txt)
            return HttpResponseRedirect(reverse("accounts-edit"))
    else:
        image_form = AvatarForm(prefix="image")

    has_granted_permissions = AccessToken.objects.filter(user=request.user).count()
    has_old_avatar = False
    if not os.path.exists(profile.locations('avatar.XL.path')) and os.path.exists(profile.locations('avatar.L.path')):
        has_old_avatar = True
    if os.path.exists(profile.locations('avatar.XL.path')) and os.path.exists(profile.locations('avatar.L.path')):
        if os.path.getsize(profile.locations('avatar.XL.path')) == os.path.getsize(profile.locations('avatar.L.path')):
            has_old_avatar = True

    tvars = {
        'user': request.user,
        'profile': profile,
        'profile_form': profile_form,
        'image_form': image_form,
        'has_granted_permissions': has_granted_permissions,
        'has_old_avatar': has_old_avatar,
        'uploads_enabled': settings.UPLOAD_AND_DESCRIPTION_ENABLED,
        'activePage': 'profile', 
    }
    return render(request, 'accounts/edit.html', tvars)


@transaction.atomic()
def handle_uploaded_image(profile, f):
    upload_logger.info("\thandling profile image upload")
    os.makedirs(os.path.dirname(profile.locations("avatar.L.path")), exist_ok=True)

    ext = os.path.splitext(os.path.basename(f.name))[1]
    tmp_image_path = tempfile.mktemp(suffix=ext, prefix=str(profile.user.id))
    try:
        upload_logger.info("\topening file: %s", tmp_image_path)
        destination = open(tmp_image_path, 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
        upload_logger.info("\tfile upload done")
    except Exception as e:
        upload_logger.info("\tfailed writing file error: %s", str(e))

    upload_logger.info("\tcreating thumbnails")
    path_s = profile.locations("avatar.S.path")
    path_m = profile.locations("avatar.M.path")
    path_l = profile.locations("avatar.L.path")
    path_xl = profile.locations("avatar.XL.path")
    try:
        extract_square(tmp_image_path, path_s, 32)
        upload_logger.info("\tcreated small thumbnail")
        profile.has_avatar = True
        profile.save()
    except Exception as e:
        upload_logger.info("\tfailed creating small thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_m, 40)
        upload_logger.info("\tcreated medium thumbnail")
    except Exception as e:
        upload_logger.info("\tfailed creating medium thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_l, 70)
        upload_logger.info("\tcreated large thumbnail")
    except Exception as e:
        upload_logger.info("\tfailed creating large thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_xl, 100)
        upload_logger.info("\tcreated extra-large thumbnail")
    except Exception as e:
        upload_logger.info("\tfailed creating extra-large thumbnails: " + str(e))

    copy_avatar_to_mirror_locations(profile)
    os.unlink(tmp_image_path)


@login_required
@transaction.atomic()
def manage_sounds(request, tab):

    def process_filter_and_sort_options(request, sort_options, tab):
        sort_by = request.GET.get('s', sort_options[0][0])
        filter_query = request.GET.get('q', '')
        try:
            sort_by_db = \
                [option_db_name for option_name, _, option_db_name in sort_options if option_name == sort_by][0]
        except IndexError:
            sort_by_db = sort_options[0][2]
        filter_db = None
        if filter_query:
            filter_db = SearchQuery(filter_query)
        return {
            'sort_by': sort_by,
            'filter_query': filter_query,
            'sort_options': sort_options,
        }, sort_by_db, filter_db
        

    # First do some stuff common to all tabs
    sounds_published_base_qs = Sound.public.filter(user=request.user)
    sounds_moderation_base_qs = \
        Sound.objects.filter(user=request.user, processing_state="OK").exclude(moderation_state="OK")
    sounds_processing_base_qs = Sound.objects.filter(user=request.user).exclude(processing_state="OK")
    sounds_published_count = sounds_published_base_qs.count()
    sounds_moderation_count = sounds_moderation_base_qs.count()
    sounds_processing_count = sounds_processing_base_qs.count()
    packs_base_qs = Pack.objects.filter(user=request.user).exclude(is_deleted=True)
    packs_count = packs_base_qs.count()
    file_structure, files = generate_tree(request.user.profile.locations()['uploads_dir'])
    sounds_pending_description_count = len(files)

    tvars = {
        'tab': tab,
        'sounds_published_count': sounds_published_count,
        'sounds_moderation_count': sounds_moderation_count,
        'sounds_processing_count': sounds_processing_count,
        'sounds_pending_description_count': sounds_pending_description_count,
        'packs_count': packs_count,
    }

    # Then do dedicated processing for each tab
    if tab == 'pending_description':
        unclosed_bulkdescribe = BulkUploadProgress.objects.filter(user=request.user).exclude(progress_type="C")
        tvars.update({'unclosed_bulkdescribe': unclosed_bulkdescribe})
        tvars_or_redirect = sounds_pending_description_helper(request, file_structure, files)
        if isinstance(tvars_or_redirect, dict):
            tvars.update(tvars_or_redirect)
        else:
            return tvars_or_redirect

    elif tab == 'packs':
        if request.POST and ('edit' in request.POST or 'delete_confirm' in request.POST):
            try:
                pack_ids = [int(part) for part in request.POST.get('object-ids', '').split(',')]
            except ValueError:
                pack_ids = []
            packs = Pack.objects.ordered_ids(pack_ids)
            # Just as a sanity check, filter out packs not owned by the user
            packs = [pack for pack in packs if pack.user == pack.user]
    
            if packs:
                if 'edit' in request.POST:
                    # There will be only one pack selected (otherwise the button is disabled)
                    # Redirect to the edit pack page
                    pack = packs[0]
                    return HttpResponseRedirect(reverse('pack-edit', args=[pack.user.username, pack.id]) + '?next=' + request.path)
                elif 'delete_confirm' in request.POST:
                    # Delete the selected packs
                    n_packs_deleted = 0
                    for pack in packs:
                        web_logger.info(f"User {request.user.username} requested to delete pack {pack.id}")
                        pack.delete_pack(remove_sounds=False)
                        n_packs_deleted += 1
                    messages.add_message(request, messages.INFO,
                                        f'Successfully deleted {n_packs_deleted} '
                                        f'pack{"s" if n_packs_deleted != 1 else ""}')
                    return HttpResponseRedirect(reverse('accounts-manage-sounds', args=[tab]))

        sort_options = [
            ('updated_desc', 'Last modified (newest first)', '-last_updated'),
            ('updated_asc', 'Last modified (oldest first)', 'last_updated'),
            ('created_desc', 'Date added (newest first)', '-created'),
            ('created_asc', 'Date added (oldest first)', 'created'),
            ('name', 'Name', 'name'),
            ('num_sounds', 'Number of sounds', 'num_sounds'),
        ]
        extra_tvars, sort_by_db, filter_db = process_filter_and_sort_options(request, sort_options, tab)
        tvars.update(extra_tvars)
        if filter_db is not None:
            packs_base_qs = packs_base_qs.annotate(search=SearchVector('name', 'id', 'description')).filter(search=filter_db).distinct()
        packs = packs_base_qs.order_by(sort_by_db)
        pack_ids = list(packs.values_list('id', flat=True))
        paginator = paginate(request, pack_ids, 12)
        tvars.update(paginator)
        packs_to_select = Pack.objects.ordered_ids(paginator['page'].object_list, exclude_deleted=False)
        for pack in packs_to_select:
            pack.show_unpublished_sounds_warning = True
        tvars['packs_to_select'] = packs_to_select

    elif tab in ['published', 'pending_moderation', 'processing']:
        # If user has selected sounds to edit or to re-process
        if request.POST and ('edit' in request.POST or 'process' in request.POST or 'delete_confirm' in request.POST):
            try:
                sound_ids = [int(part) for part in request.POST.get('object-ids', '').split(',')]
            except ValueError:
                sound_ids = []
            sounds = Sound.objects.ordered_ids(sound_ids)
            # Just as a sanity check, filter out sounds not owned by the user
            sounds = [sound for sound in sounds if sound.user == request.user]
            if sounds:
                if 'edit' in request.POST:
                    # Edit the selected sounds
                    session_key_prefix = str(uuid.uuid4())[0:8]  # Use a new so we don't interfere with other active description/editing processes
                    request.session[f'{session_key_prefix}-edit_sounds'] = sounds  # Add the list of sounds to edit in the session object
                    request.session[f'{session_key_prefix}-len_original_edit_sounds'] = len(sounds)
                    return HttpResponseRedirect(reverse('accounts-edit-sounds') + f'?next={request.path}&session={session_key_prefix}')
                elif 'delete_confirm' in request.POST:
                    # Delete the selected sounds
                    n_sounds_deleted = 0
                    for sound in sounds:
                        web_logger.info(f"User {request.user.username} requested to delete sound {sound.id}")
                        try:
                            ticket = sound.ticket
                            tc = TicketComment(
                                sender=request.user,
                                text=f"User {request.user} deleted the sound",
                                ticket=ticket,
                                moderator_only=False)
                            tc.save()
                        except Ticket.DoesNotExist:
                            pass
                        sound.delete()
                        n_sounds_deleted += 1
                    messages.add_message(request, messages.INFO,
                                         f'Successfully deleted {n_sounds_deleted} '
                                         f'sound{"s" if n_sounds_deleted != 1 else ""}')
                    return HttpResponseRedirect(reverse('accounts-manage-sounds', args=[tab]))

                elif 'process' in request.POST:
                    # Send selected sounds to re-process
                    n_send_to_processing = 0
                    for sound in sounds:
                        if sound.process():
                            n_send_to_processing += 1
                    sounds_skipped_msg_part = ''
                    if n_send_to_processing != len(sounds):
                        sounds_skipped_msg_part = f' {len(sounds) - n_send_to_processing} sounds were not send to ' \
                                                  f'processing due to many failed processing attempts.'
                    messages.add_message(request, messages.INFO,
                                         f'Sent { n_send_to_processing } '
                                         f'sound{ "s" if n_send_to_processing != 1 else "" } '
                                         f'to re-process.{ sounds_skipped_msg_part }')
                    return HttpResponseRedirect(reverse('accounts-manage-sounds', args=[tab]))
    
        # Process query and filter options
        sort_options = [
            ('created_desc', 'Date added (newest first)', '-created'),
            ('created_asc', 'Date added (oldest first)', 'created'),
            ('name', 'Name', 'original_filename'),
        ]
        extra_tvars, sort_by_db, filter_db = process_filter_and_sort_options(request, sort_options, tab)
        tvars.update(extra_tvars)

        # Select relevant sound ids depending on tab/filters
        if tab == 'published':
            sounds = sounds_published_base_qs
        elif tab == 'pending_moderation':
            sounds = sounds_moderation_base_qs
        elif tab == 'processing':
            sounds = sounds_processing_base_qs
        if filter_db is not None:
            sounds = sounds.annotate(search=SearchVector('original_filename', 'id', 'description', 'tags__tag__name')).filter(search=filter_db).distinct()
        sounds = sounds.order_by(sort_by_db)
        sound_ids = list(sounds.values_list('id', flat=True))

        # Paginate and get corresponding sound objects
        paginator = paginate(request, sound_ids, 9)
        tvars.update(paginator)
        sounds_to_select = Sound.objects.ordered_ids(paginator['page'].object_list)
        for sound in sounds_to_select:
            # We set these properties below so display_sound templatetag adds a bit more info to the sound display
            if tab == 'pending_moderation':
                sound.show_moderation_ticket = True
            elif tab == 'processing':
                sound.show_processing_status = True
        tvars['sounds_to_select'] = sounds_to_select
    else:
        raise Http404  # Non-existing tab

    return render(request, 'accounts/manage_sounds.html', tvars)


@login_required
@transaction.atomic()
def edit_sounds(request):
    session_key_prefix = request.GET.get('session', '')
    return edit_and_describe_sounds_helper(request, session_key_prefix=session_key_prefix)  # Note that the list of sounds to describe is stored in the session object


def sounds_pending_description_helper(request, file_structure, files):
    file_structure.name = ''

    if request.method == 'POST':
        form = FileChoiceForm(files, request.POST, prefix='sound')
        csv_form = BulkDescribeForm(request.POST, request.FILES, prefix='bulk')
        if csv_form.is_valid():
            directory = os.path.join(settings.CSV_PATH, str(request.user.id))
            os.makedirs(directory, exist_ok=True)
            extension = csv_form.cleaned_data['csv_file'].name.rsplit('.', 1)[-1].lower()
            new_csv_filename = str(uuid.uuid4()) + f'.{extension}'
            path = os.path.join(directory, new_csv_filename)
            destination = open(path, 'wb')

            f = csv_form.cleaned_data['csv_file']
            for chunk in f.chunks():
                destination.write(chunk)
            destination.close()

            bulk = BulkUploadProgress.objects.create(user=request.user, csv_filename=new_csv_filename,
                                                     original_csv_filename=f.name)
            tasks.validate_bulk_describe_csv.delay(bulk_upload_progress_object_id=bulk.id)
            return HttpResponseRedirect(reverse("accounts-bulk-describe", args=[bulk.id]))
        elif form.is_valid():
            if "delete_confirm" in request.POST:
                for f in form.cleaned_data["files"]:
                    try:
                        os.remove(files[f].full_path)
                        utils.sound_upload.clean_processing_before_describe_files(files[f].full_path)
                        remove_uploaded_file_from_mirror_locations(files[f].full_path)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            upload_logger.info("Failed to remove file %s", str(e))
                        else:
                            raise

                # Remove user uploads directory if there are no more files to describe
                user_uploads_dir = request.user.profile.locations()['uploads_dir']
                remove_directory_if_empty(user_uploads_dir)
                remove_empty_user_directory_from_mirror_locations(user_uploads_dir)
                return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['pending_description']))
            elif "describe" in request.POST:
                session_key_prefix = str(uuid.uuid4())[0:8]  # Use a new so we don't interfere with other active description/editing processes
                request.session[f'{session_key_prefix}-describe_sounds'] = [files[x] for x in form.cleaned_data["files"]]
                request.session[f'{session_key_prefix}-len_original_describe_sounds'] = len(request.session[f'{session_key_prefix}-describe_sounds'])
                # If only one file is choosen, go straight to the last step of the describe process, otherwise go to license selection step
                if len(request.session[f'{session_key_prefix}-describe_sounds']) > 1:
                    return HttpResponseRedirect(reverse('accounts-describe-license') + f'?session={session_key_prefix}')
                else:
                    return HttpResponseRedirect(reverse('accounts-describe-sounds') + f'?session={session_key_prefix}')
            else:
                form = FileChoiceForm(files)
                tvars = {'form': form, 'file_structure': file_structure}
                return tvars
    else:
        csv_form = BulkDescribeForm(prefix='bulk')
        form = FileChoiceForm(files, prefix='sound')
    tvars = {
        'form': form,
        'file_structure': file_structure,
        'n_files': len(files),
        'csv_form': csv_form,
        'describe_enabled': settings.UPLOAD_AND_DESCRIPTION_ENABLED
    }
    return tvars


@login_required
def describe_license(request):
    session_key_prefix = request.GET.get('session', '')
    if request.method == 'POST':
        form = LicenseForm(request.POST, hide_old_license_versions=True)
        if form.is_valid():
            request.session[f'{session_key_prefix}-describe_license'] = form.cleaned_data['license']
            return HttpResponseRedirect(reverse('accounts-describe-pack') + f'?session={session_key_prefix}')
    else:
        form = LicenseForm(hide_old_license_versions=True)
    tvars = {
        'form': form, 
        'num_files': request.session.get(f'{session_key_prefix}-len_original_describe_sounds', 0), 
        'session_key_prefix': session_key_prefix
    }
    return render(request, 'accounts/describe_license.html', tvars)


@login_required
def describe_pack(request):
    packs = Pack.objects.filter(user=request.user).exclude(is_deleted=True)
    session_key_prefix = request.GET.get('session', '')
    if request.method == 'POST':
        form = PackForm(packs, request.POST, prefix="pack")
        if form.is_valid():
            data = form.cleaned_data
            if data['new_pack']:
                pack, created = Pack.objects.get_or_create(user=request.user, name=data['new_pack'])
                request.session[f'{session_key_prefix}-describe_pack'] = pack
            elif data['pack']:
                request.session[f'{session_key_prefix}-describe_pack'] = data['pack']
            else:
                request.session[f'{session_key_prefix}-describe_pack'] = False
            return HttpResponseRedirect(reverse('accounts-describe-sounds') + f'?session={session_key_prefix}')
    else:
        form = PackForm(packs, prefix="pack")
    tvars = {
        'form': form, 
        'num_files': request.session.get(f'{session_key_prefix}-len_original_describe_sounds', 0), 
        'session_key_prefix': session_key_prefix
    }
    return render(request, 'accounts/describe_pack.html', tvars)


@login_required
@transaction.atomic()
def describe_sounds(request):
    session_key_prefix = request.GET.get('session', '')
    return edit_and_describe_sounds_helper(request, describing=True, session_key_prefix=session_key_prefix)  # Note that the list of sounds to describe is stored in the session object

    
@login_required
def attribution(request):
    qs_sounds = Download.objects.annotate(download_type=Value("sound", CharField()))\
        .values('download_type', 'sound_id', 'sound__user__username', 'sound__original_filename',
                'license__name', 'license__deed_url', 'sound__license__name', 'sound__license__deed_url', 'created').filter(user=request.user)
    qs_packs = PackDownload.objects.annotate(download_type=Value("pack", CharField()))\
        .values('download_type', 'pack_id', 'pack__user__username', 'pack__name', 'pack__name', 'pack__name',
                'pack__name', 'pack__name', 'created').filter(user=request.user)
    # NOTE: in the query above we duplicate 'pack__name' so that qs_packs has same num columns than qs_sounds. This is
    # a requirement for doing QuerySet.union below. Also as a result of using QuerySet.union, the names of the columns
    # (keys in each dictionary element) are unified and taken from the main query set. This means that after the union,
    # queryset entries corresponding to PackDownload will have corresponding field names from entries corresponding to
    # Download. Therefore to access the pack_id (which is the second value in the list), you'll need to do
    # item['sound_id'] instead of item ['pack_id']. See the template of this view for an example of this.
    qs = qs_sounds.union(qs_packs).order_by('-created')

    tvars = {'format': request.GET.get("format", "regular")}
    tvars.update(paginate(request, qs, 40))
    return render(request, 'accounts/attribution.html', tvars)


@login_required
def download_attribution(request):
    content = {'csv': 'csv', 
               'txt': 'plain',
               'json': 'json'}

    qs_sounds = Download.objects.annotate(download_type=Value('sound', CharField()))\
        .values('download_type', 'sound_id', 'sound__user__username', 'sound__original_filename',
                'license__name', 'license__deed_url', 'sound__license__name', 'sound__license__deed_url', 'created').filter(user=request.user)
    qs_packs = PackDownload.objects.annotate(download_type=Value('pack', CharField()))\
        .values('download_type', 'pack_id', 'pack__user__username', 'pack__name', 'pack__name', 'pack__name',
                'pack__name', 'pack__name', 'created').filter(user=request.user)
    # NOTE: see the above view, attribution. Note that we need to use .encode('utf-8') in some fields that can contain
    # non-ascii characters even if these seem wrongly named due to the fact of using .union() in the QuerySet.
    qs = qs_sounds.union(qs_packs).order_by('-created')

    download = request.GET.get('dl', '')
    now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'{request.user}_{now}_attribution.{download}'
    if download in ['csv', 'txt']:
        response = HttpResponse(content_type=f'text/{content[download]}')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        output = io.StringIO()
        if download == 'csv':
            output.write('Download Type,File Name,User,License,Timestamp\r\n')
            csv_writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for row in qs:
                csv_writer.writerow(
                    [row['download_type'][0].upper(), row['sound__original_filename'],
                     row['sound__user__username'],
                     license_with_version(row['license__name'] or row['sound__license__name'],
                                          row['license__deed_url'] or row['sound__license__deed_url']),
                     row['created']])
        elif download == 'txt':
            for row in qs:
                output.write("{}: {} by {} | License: {} | Timestamp: {}\n".format(row['download_type'][0].upper(),
                             row['sound__original_filename'], row['sound__user__username'],
                             license_with_version(row['license__name'] or row['sound__license__name'],
                                                  row['license__deed_url'] or row['sound__license__deed_url']),
                             row['created']))
        response.writelines(output.getvalue())
        return response
    elif download == 'json':
        output = []
        for row in qs:
            if row['download_type'][0].upper() == 'S':
                output.append({
                    'sound_url': url2absurl(reverse("sound", args=[row['sound__user__username'], row['sound_id']])),
                    'sound_name': row['sound__original_filename'],
                    'author_url': url2absurl(reverse("account", args=[row['sound__user__username']])),
                    'author_name': row['sound__user__username'],
                    'license_url': row['license__deed_url'] or row['sound__license__deed_url'],
                    'license_name': license_with_version(row['license__name'] or row['sound__license__name'],
                                    row['license__deed_url'] or row['sound__license__deed_url']),
                    'timestamp': str(row['created'])
                })
            elif row['download_type'][0].upper() == 'P':
                output.append({
                    'pack_url': url2absurl(reverse("pack", args=[row['sound__user__username'], row['sound_id']])),
                    'pack_name': row['sound__original_filename'],
                    'author_url': url2absurl(reverse("account", args=[row['sound__user__username']])),
                    'author_name': row['sound__user__username'],
                    'license_url': row['license__deed_url'] or row['sound__license__deed_url'],
                    'license_name': license_with_version(row['license__name'] or row['sound__license__name'],
                                    row['license__deed_url'] or row['sound__license__deed_url']),
                    'timestamp': str(row['created'])
                })
        return JsonResponse(output, safe=False)
    else:
        return HttpResponseRedirect(reverse('accounts-attribution'))


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def downloaded_sounds(request, username):
    if not request.GET.get('ajax'):
        # If not loading as a modal, redirect to the account page with parameter to open modal
        return HttpResponseRedirect(reverse('account', args=[username]) + '?downloaded_sounds=1')
    user = request.parameter_user
    qs = Download.objects.filter(user_id=user.id).order_by('-created')
    num_items_per_page = settings.DOWNLOADED_SOUNDS_PACKS_PER_PAGE
    paginator = paginate(request, qs, num_items_per_page, object_count=user.profile.num_sound_downloads)
    page = paginator["page"]
    sound_ids = [d.sound_id for d in page]
    sounds_dict = Sound.objects.dict_ids(sound_ids)
    download_list = []
    for d in page:
        sound = sounds_dict.get(d.sound_id, None)
        if sound is not None:
            download_list.append({"created": d.created, "sound": sound})
    tvars = {"username": username,
            "user": user,
            "download_list": download_list,
            "type_sounds": True}
    tvars.update(paginator)
    return render(request, 'accounts/modal_downloads.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def downloaded_packs(request, username):
    if not request.GET.get('ajax'):
        # If not loaded as a modal, redirect to account page with parameter to open modal
        return HttpResponseRedirect(reverse('account', args=[username]) + '?downloaded_packs=1')
    user = request.parameter_user
    qs = PackDownload.objects.filter(user=user.id).order_by('-created')
    num_items_per_page = settings.DOWNLOADED_SOUNDS_PACKS_PER_PAGE
    paginator = paginate(request, qs, num_items_per_page, object_count=user.profile.num_pack_downloads)
    page = paginator["page"]
    pack_ids = [d.pack_id for d in page]
    packs_dict = Pack.objects.dict_ids(pack_ids)
    download_list = []
    for d in page:
        pack = packs_dict.get(d.pack_id, None)
        if pack is not None:
            download_list.append({"created": d.created, "pack": pack})
    tvars = {"username": username,
            "download_list": download_list,
            "type_sounds": False}
    tvars.update(paginator)
    return render(request, 'accounts/modal_downloads.html', tvars)


def latest_content_type(scores):
    if scores['uploads'] >= scores['posts'] and scores['uploads'] >= scores['comments']:
        return 'sound'
    elif scores['posts'] >= scores['uploads'] and scores['posts'] > scores['comments']:
        return 'post'
    elif scores['comments'] >= scores['uploads'] and scores['comments'] > scores['posts']:
        return 'comment'


def create_user_rank(uploaders, posters, commenters, weights=dict()):
    upload_weight = weights.get('upload', 1)
    post_weight = weights.get('post', 0.4)
    comment_weight = weights.get('comment', 0.05)
    user_rank = {}
    for user in uploaders:
        user_rank[user['user']] = {'uploads': user['id__count'], 'posts': 0, 'comments': 0, 'score': 0}
    for user in posters:
        if user['author_id'] in user_rank:
            user_rank[user['author_id']]['posts'] = user['id__count']
        else:
            user_rank[user['author_id']] = {'uploads': 0, 'posts': user['id__count'], 'comments': 0, 'score': 0}
    for user in commenters:
        if user['user_id'] in user_rank:
            user_rank[user['user_id']]['comments'] = user['id__count']
        else:
            user_rank[user['user_id']] = {'uploads': 0, 'posts': 0, 'comments': user['id__count'], 'score': 0}
    sort_list = []
    for user in user_rank:
        user_rank[user]['score'] = user_rank[user]['uploads'] * upload_weight + \
            user_rank[user]['posts'] * post_weight + user_rank[user]['comments'] * comment_weight
        sort_list.append([user_rank[user]['score'], user])
    return user_rank, sort_list


def accounts(request):
    return HttpResponseRedirect(reverse('charts'))


def compute_charts_stats():
    num_days = 14
    num_items = 10
    last_time = DBTime.get_last_time() - datetime.timedelta(num_days)
    weights = settings.BW_CHARTS_ACTIVE_USERS_WEIGHTS

    # Most active users in last num_days
    latest_uploaders = Sound.public.filter(created__gte=last_time).values("user").annotate(Count('id'))\
        .order_by("-id__count")
    latest_posters = Post.objects.filter(created__gte=last_time).values("author_id").annotate(Count('id'))\
        .order_by("-id__count")
    latest_commenters = Comment.objects.filter(created__gte=last_time).values("user_id").annotate(Count('id'))\
        .order_by("-id__count")
    user_rank, sort_list = create_user_rank(latest_uploaders, latest_posters, latest_commenters, weights=weights)
    most_active_users = User.objects.select_related("profile")\
        .filter(id__in=[u[1] for u in sorted(sort_list, reverse=True)[:num_items]])
    most_active_users_display = [[u, user_rank[u.id]] for u in most_active_users]
    most_active_users_display = sorted(most_active_users_display,
                                       key=lambda usr: user_rank[usr[0].id]['score'],
                                       reverse=True)

    # Newest active users
    new_user_in_rank_ids = User.objects.filter(date_joined__gte=last_time, id__in=list(user_rank.keys()))\
        .values_list('id', flat=True)
    new_user_objects = {user.id: user for user in
                        User.objects.select_related("profile").filter(date_joined__gte=last_time)
                            .filter(id__in=new_user_in_rank_ids)}
    new_users_display = [(new_user_objects[user_id], user_rank[user_id]) for user_id in new_user_in_rank_ids]
    new_users_display = sorted(new_users_display, key=lambda x: x[1]['score'], reverse=True)[:num_items]

    # Top recent uploaders (by count and by length)
    top_recent_uploaders_by_count = Sound.public \
        .filter(created__gte=last_time) \
        .values('user_id').annotate(n_sounds=Count('user_id')) \
        .order_by('-n_sounds')[0:num_items]
    user_objects = {user.id: user for user in
                    User.objects.filter(id__in=[item['user_id'] for item in top_recent_uploaders_by_count])}
    top_recent_uploaders_by_count_display = [
        (user_objects[item['user_id']].profile.locations("avatar.M.url"),
         user_objects[item['user_id']].username,
         item['n_sounds']) for item in top_recent_uploaders_by_count]

    top_recent_uploaders_by_length = Sound.public \
         .filter(created__gte=last_time) \
         .values('user_id').annotate(total_duration=Sum('duration')) \
         .order_by('-total_duration')[0:num_items]
    user_objects = {user.id: user for user in
                    User.objects.filter(id__in=[item['user_id'] for item in top_recent_uploaders_by_length])}
    top_recent_uploaders_by_length_display = [
        (user_objects[item['user_id']].profile.locations("avatar.M.url"),
         user_objects[item['user_id']].username,
         item['total_duration']) for item in top_recent_uploaders_by_length]

    # All time top uploaders (by count and by length)
    all_time_top_uploaders_by_count = Sound.public \
        .values('user_id').annotate(n_sounds=Count('user_id')) \
        .order_by('-n_sounds')[0:num_items]
    user_objects = {user.id: user for user in
                    User.objects.filter(id__in=[item['user_id'] for item in all_time_top_uploaders_by_count])}
    all_time_top_uploaders_by_count_display = [
        (user_objects[item['user_id']].profile.locations("avatar.M.url"),
         user_objects[item['user_id']].username,
         item['n_sounds']) for item in all_time_top_uploaders_by_count]

    all_time_top_uploaders_by_length = Sound.public \
         .values('user_id').annotate(total_duration=Sum('duration')) \
         .order_by('-total_duration')[0:num_items]
    user_objects = {user.id: user for user in
                    User.objects.filter(id__in=[item['user_id'] for item in all_time_top_uploaders_by_length])}
    all_time_top_uploaders_by_length_display = [
        (user_objects[item['user_id']].profile.locations("avatar.M.url"),
         user_objects[item['user_id']].username,
         item['total_duration']) for item in all_time_top_uploaders_by_length]

    return {
        'num_days': num_days,
        'recent_most_active_users': most_active_users_display,
        'new_active_users': new_users_display,
        'top_recent_uploaders_by_count': top_recent_uploaders_by_count_display,
        'top_recent_uploaders_by_length': top_recent_uploaders_by_length_display,
        'all_time_top_uploaders_by_count': all_time_top_uploaders_by_count_display,
        'all_time_top_uploaders_by_length': all_time_top_uploaders_by_length_display
    }


def charts(request):
    """
    This view shows some general Freesound use statistics. Some of the queries can be a bit so their results
    should be in the cache and generated by a cron job. If not found there, the view will compute the stats
    and cache them.
    """
    tvars = cache.get(settings.CHARTS_DATA_CACHE_KEY, None)
    if tvars is None:
        tvars = compute_charts_stats()
        cache.set(settings.CHARTS_DATA_CACHE_KEY, tvars, 60 * 60 * 24)
    return render(request, 'accounts/charts.html', tvars)


@redirect_if_old_username_or_404
def account(request, username):
    user = request.parameter_user
    latest_sounds = list(Sound.objects.bulk_sounds_for_user(user.id, settings.SOUNDS_PER_PAGE_PROFILE_PACK_PAGE))
    following = follow_utils.get_users_following_qs(user)
    followers = follow_utils.get_users_followers_qs(user)
    following_tags = follow_utils.get_tags_following_qs(user)
    follow_user_url = reverse('follow-user', args=[username])
    unfollow_user_url = reverse('unfollow-user', args=[username])
    show_unfollow_button = request.user.is_authenticated and follow_utils.is_user_following_user(request.user, user)
    has_bookmarks = Bookmark.objects.filter(user=user).exists()
    if not user.is_active:
        messages.add_message(request, messages.INFO, 'This account has <b>not been activated</b> yet.')
    if request.user.has_perm('tickets.can_moderate'):
        num_sounds_pending = user.profile.num_sounds_pending_moderation()
        num_mod_annotations = UserAnnotation.objects.filter(user=user).count()
    else:
        num_sounds_pending = None
        num_mod_annotations = None

    show_about = ((request.user == user)  # user is looking at own page
                  or request.user.is_superuser  # admins should always see about fields
                  or user.is_superuser  # no reason to hide admin's about fields
                  or user.profile.get_total_downloads > 0  # user has downloads
                  or user.profile.num_sounds > 0)  # user has uploads

    last_geotags_serialized = []
    if user.profile.has_geotags and settings.MAPBOX_USE_STATIC_MAPS_BEFORE_LOADING:
        for sound in Sound.public.select_related('geotag').filter(user__username__iexact=username).exclude(geotag=None)[0:10]:
            last_geotags_serialized.append({'lon': sound.geotag.lon, 'lat': sound.geotag.lat})
        last_geotags_serialized = json.dumps(last_geotags_serialized)

    tvars = {
        'home': request.user == user,
        'user': user,
        'latest_sounds': latest_sounds,
        'follow_user_url': follow_user_url,
        'following': following,
        'followers': followers,
        'following_tags': following_tags,
        'unfollow_user_url': unfollow_user_url,
        'show_unfollow_button': show_unfollow_button,
        'has_bookmarks': has_bookmarks,
        'show_about': show_about,
        'num_sounds_pending': num_sounds_pending,
        'num_mod_annotations': num_mod_annotations,
        'following_modal_page': request.GET.get('following', 1),
        'followers_modal_page': request.GET.get('followers', 1),
        'following_tags_modal_page': request.GET.get('followingTags', 1),
        'last_geotags_serialized': last_geotags_serialized, 
        'user_downloads_public': settings.USER_DOWNLOADS_PUBLIC,
    }
    return render(request, 'accounts/account.html', tvars)


@redirect_if_old_username_or_404
def account_stats_section(request, username):
    if not request.GET.get('ajax'):
        raise Http404  # Only accessible via ajax
    user = request.parameter_user
    tvars = {
        'user': user,
        'user_stats': user.profile.get_stats_for_profile_page(),
    }
    return render(request, 'accounts/account_stats_section.html', tvars)


@redirect_if_old_username_or_404
def account_latest_packs_section(request, username):
    if not request.GET.get('ajax'):
        raise Http404  # Only accessible via ajax
    
    user = request.parameter_user
    tvars = {
        'user': user,
        # Note we don't pass latest packs data because it is requested from the template
        # if there is no cache available
    }
    return render(request, 'accounts/account_latest_packs_section.html', tvars)


def handle_uploaded_file(user_id, f):
    # Move or copy the uploaded file from the temporary folder created by Django to the /uploads path
    dest_directory = os.path.join(settings.UPLOADS_PATH, str(user_id))
    os.makedirs(dest_directory, exist_ok=True)
    dest_path = os.path.join(dest_directory, os.path.basename(f.name)).encode("utf-8")
    upload_logger.info(f"handling file upload and saving to {dest_path}")
    starttime = time.time()
    if settings.MOVE_TMP_UPLOAD_FILES_INSTEAD_OF_COPYING and isinstance(f, TemporaryUploadedFile):
        # Big files (bigger than ~2MB, this is configured by Django and can be customized) will be delivered via a
        # TemporaryUploadedFile which has already been streamed in disk, so we only need to move the already existing
        # file instead of copying it
        try:
            os.rename(f.temporary_file_path(), dest_path)
            os.chmod(dest_path, 0o644)  # Set appropriate permissions so that file can be downloaded from nginx
        except Exception as e:
            upload_logger.warning("failed moving TemporaryUploadedFile error: %s", str(e))
            return False
    else:
        # Small files will be of type InMemoryUploadedFile instead of TemporaryUploadedFile and will be initially
        # stored in memory, so we need to copy them to the destination
        try:
            destination = open(dest_path, 'wb')
            for chunk in f.chunks():
                destination.write(chunk)
        except Exception as e:
            upload_logger.warning("failed writing uploaded file error: %s", str(e))
            return False

    # trigger processing of uploaded files before description
    tasks.process_before_description.delay(audio_file_path=dest_path.decode())
    upload_logger.info(f"sent uploaded file {dest_path} to processing before description")

    # NOTE: if we enable mirror locations for uploads and the copying below causes problems, we could do it async
    copy_uploaded_file_to_mirror_locations(dest_path)
    upload_logger.info(f"handling file upload done, took {time.time() - starttime:.2f} seconds")
    return True


@csrf_exempt
def upload_file(request):
    """ upload a file. This function does something weird: it gets the session id from the
    POST variables. This is weird but... as far as we know it's not too bad as we only need
    the user login """

    upload_logger.info("start uploading file")
    engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])  # get the current session engine
    session_data = engine.SessionStore(request.POST.get('sessionid', ''))
    try:
        user_id = session_data['_auth_user_id']
        upload_logger.info("\tuser id %s", str(user_id))
    except KeyError:
        upload_logger.warning("failed to get user id from session")
        return HttpResponseBadRequest("You're not logged in. Log in and try again.")
    try:
        request.user = User.objects.get(id=user_id)
        upload_logger.info("\tfound user: %s", request.user.username)
    except User.DoesNotExist:
        upload_logger.warning("user with this id does not exist")
        return HttpResponseBadRequest("user with this ID does not exist.")

    if request.method == 'POST':
        form = FlashUploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            upload_logger.info("\tform data is valid")
            if handle_uploaded_file(user_id, request.FILES["file"]):
                return HttpResponse("File uploaded OK")
            else:
                return HttpResponseServerError("Error in file upload")
        else:
            upload_logger.warning("form data is invalid: %s", str(form.errors))
            return HttpResponseBadRequest("Form is not valid.")
    else:
        upload_logger.warning("no data in post")
        return HttpResponseBadRequest("No POST data in request")


@login_required
def upload(request, no_flash=False):
    form = UploadFileForm()
    successes = 0
    errors = []
    uploaded_file = None
    if no_flash:
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                submitted_files = request.FILES.getlist('files')
                files_names = list()
                for file_ in submitted_files:
                    #check for duplicated names and add an identifier, otherwise, different files with the same
                    #name will be overwritten in the description queue
                    if file_.name in files_names:                        
                        name_counter = files_names.count(file_.name) 
                        files_names.append(file_.name) 
                        name, extension = os.path.splitext(file_.name)
                        file_.name = "%s(%d)%s" % (name, name_counter, extension) 
                    else:
                        files_names.append(file_.name)
                    
                    if handle_uploaded_file(request.user.id, file_):
                        uploaded_file = file_
                        successes += 1
                    else:
                        errors.append(file_)
    tvars = {
        'form': form,
        'uploaded_file': uploaded_file,
        'successes': successes,
        'errors': errors,
        'no_flash': no_flash,
        'max_file_size': settings.UPLOAD_MAX_FILE_SIZE_COMBINED,
        'max_file_size_in_MB': int(round(settings.UPLOAD_MAX_FILE_SIZE_COMBINED * 1.0 / (1024 * 1024))),
        'lossless_file_extensions': [ext for ext in settings.ALLOWED_AUDIOFILE_EXTENSIONS if ext not in settings.LOSSY_FILE_EXTENSIONS],
        'lossy_file_extensions': settings.LOSSY_FILE_EXTENSIONS,
        'all_file_extensions': settings.ALLOWED_AUDIOFILE_EXTENSIONS,
        'uploads_enabled': settings.UPLOAD_AND_DESCRIPTION_ENABLED
    }
    return render(request, 'accounts/upload.html', tvars)


@login_required
def bulk_describe(request, bulk_id):
    if not request.user.profile.can_do_bulk_upload():
        messages.add_message(request, messages.INFO, "Your user does not have permission to use the bulk describe "
                                                     "feature. You must upload at least %i sounds before being able"
                                                     "to use that feature." % settings.BULK_UPLOAD_MIN_SOUNDS)
        return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['pending_description']))

    bulk = get_object_or_404(BulkUploadProgress, id=int(bulk_id), user=request.user)

    if request.POST:
        if 'start' in request.POST and bulk.progress_type == 'V':
            # If action is "start" and CSV is validated, mark BulkUploadProgress as "stared" and start describing sounds
            bulk.progress_type = 'S'
            bulk.save()
            tasks.bulk_describe.delay(bulk_upload_progress_object_id=bulk.id)

        elif 'delete' in request.POST and bulk.progress_type in ['N', 'V']:
            # If action is "delete", delete BulkUploadProgress object and go back to describe page
            bulk.delete()
            return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['pending_description']))

        elif 'close' in request.POST:
            # If action is "close", set the BulkUploadProgress object to closed state and redirect to home
            bulk.progress_type = 'C'
            bulk.save()
            return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['pending_description']))

    # Get progress info to be display if sound description process has started
    progress_info = bulk.get_description_progress_info()

    # Auto-reload if in "not yet validated" or in "started" state
    auto_reload_page = bulk.progress_type == 'N' or bulk.progress_type == 'S'

    if bulk.progress_type == 'F' and progress_info['progress_percentage'] < 100:
        # If the description process has finished but progress is still not 100 (some sounds are still processing),
        # then do the auto-reload
        auto_reload_page = True

    tvars = {
        'bulk': bulk,
        'lines_validated_ok': bulk.validation_output['lines_ok'] if bulk.validation_output else [],
        'lines_failed_validation': bulk.validation_output['lines_with_errors'] if bulk.validation_output else [],
        'global_errors': bulk.validation_output['global_errors'] if bulk.validation_output else [],
        'auto_reload_page': auto_reload_page,
        'progress_info': progress_info,
    }
    return render(request, 'accounts/bulk_describe.html', tvars)


@login_required
@transaction.atomic()
def delete(request):
    num_sounds = request.user.sounds.all().count()
    if request.method == 'POST':
        form = DeleteUserForm(request.POST, user_id=request.user.id)
        if not form.is_valid():
            form.reset_encrypted_link(request.user.id)
        else:
            # Check if a deletion request already exist and not allow user to continue if
            # that is the case. In this way we avoid duplicating deletion tasks
            cutoff_date = datetime.datetime.today() - datetime.timedelta(days=1)
            recent_pending_deletion_requests_exist = UserDeletionRequest.objects\
                .filter(user_to_id=request.user.id, last_updated__gt=cutoff_date)\
                .filter(status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED).exists()                
            if recent_pending_deletion_requests_exist:
                messages.add_message(request, messages.INFO,
                    f'It looks like a deletion action was already triggered for your user account and '
                    f'your account should be deleted shortly. If you see the account not being deleted, '
                    f'please contact us using the <a href="{reverse("contact")}">contact form</a>.')
            else:
                delete_sounds =\
                    form.cleaned_data['delete_sounds'] == 'delete_sounds'
                delete_action = DELETE_USER_DELETE_SOUNDS_ACTION_NAME if delete_sounds \
                    else DELETE_USER_KEEP_SOUNDS_ACTION_NAME
                delete_reason = DeletedUser.DELETION_REASON_SELF_DELETED
                web_logger.info(f'Requested async deletion of user {request.user.id} - {delete_action}')

                # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
                UserDeletionRequest.objects.create(user_from=request.user,
                                                user_to=request.user,
                                                status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                                                triggered_deletion_action=delete_action,
                                                triggered_deletion_reason=delete_reason)

                # Trigger async task so user gets deleted asynchronously
                tasks.delete_user.delay(user_id=request.user.id, deletion_action=delete_action, deletion_reason=delete_reason)

                # Show a message to the user that the account will be deleted shortly
                messages.add_message(request, messages.INFO,
                                    'Your user account will be deleted in a few moments. Note that this process could '
                                    'take up to several hours for users with many uploaded sounds.')

                # Logout user, mark account inctive, set unusable password and change email to a dummy one so that
                # user can't recover the account while it is being delete asynchronously
                # Note that some of these actions are also done in the delete_user method of the Profile model, but
                # we need to do them here as well before the async task is triggered and to make sure user can't
                # login even if the deletion task fails.
                request.user.set_unusable_password()
                request.user.is_active = False
                request.user.email = f'deleted_user_{request.user.id}@freesound.org'
                request.user.save()
                logout(request)
                return HttpResponseRedirect(reverse("front-page"))
    else:
        form = DeleteUserForm(user_id=request.user.id)

    tvars = {
            'delete_form': form,
            'num_sounds': num_sounds,
            'activePage': 'account',
    }
    return render(request, 'accounts/delete.html', tvars)


def old_user_link_redirect(request):
    user_id = request.GET.get('id', False)
    if user_id:
        try:
            user = get_object_or_404(User, id=int(user_id))
            return HttpResponsePermanentRedirect(reverse("account", args=[user.username]))
        except ValueError:
            raise Http404
    else:
        raise Http404


@login_required
@transaction.atomic()
def email_reset(request):
    if request.method == "POST":
        form = EmailResetForm(request.POST, user=request.user, label_suffix='')
        if form.is_valid():
            # First check that email is not already on the database, if it's already used we don't do anything.
            try:
                user = User.objects.get(email__iexact=form.cleaned_data['email'])
            except User.DoesNotExist:
                user = None
            # Check password is OK
            if user is None and request.user.check_password(form.cleaned_data["password"]):
                # Save new email info to DB (temporal)
                try:
                    rer = ResetEmailRequest.objects.get(user=request.user)
                    rer.email = form.cleaned_data['email']
                    rer.save()
                except ResetEmailRequest.DoesNotExist:
                    rer = ResetEmailRequest.objects.create(user=request.user, email=form.cleaned_data['email'])

                # Send email to the new address
                user = request.user
                email = form.cleaned_data["email"]
                tvars = {
                    'uid': int_to_base36(user.id),
                    'user': user,
                    'token': default_token_generator.make_token(user)
                }
                send_mail_template(settings.EMAIL_SUBJECT_EMAIL_CHANGED,
                                   'emails/email_reset_email.txt', tvars,
                                   email_to=email)

            return HttpResponseRedirect(reverse('accounts-email-reset-done'))
    else:
        form = EmailResetForm(user=request.user, label_suffix='')
    tvars = {
        'form': form,
        'user': request.user,
        'activePage': 'email'
    }
    return render(request, 'accounts/email_reset_form.html', tvars)


def email_reset_done(request):
    return render(request, 'accounts/email_reset_done.html', {
        'activePage': 'email'
    })


@never_cache
@login_required
@transaction.atomic()
def email_reset_complete(request, uidb36=None, token=None):
    # Check that the link is valid and the base36 corresponds to a user id
    assert uidb36 is not None and token is not None  # checked by URLconf
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
    except (ValueError, User.DoesNotExist):
        raise Http404

    # Check that the user makind the request is the same user in the base36 data
    if request.user != user:
        raise Http404

    # Retreive the new mail from the DB
    try:
        rer = ResetEmailRequest.objects.get(user=user)
    except ResetEmailRequest.DoesNotExist:
        raise Http404

    # Change the mail in the DB
    old_email = user.email
    user.email = rer.email
    user.save()

    # Remove temporal mail change information from the DB
    ResetEmailRequest.objects.get(user=user).delete()

    # NOTE: no need to clear existing EmailBounce objects associated to this user here because it is done in
    # a User deletion pre_save hook if we detect that email has changed

    # Send email to the old address notifying about the change
    tvars = {
        'old_email': old_email,
        'user': user,
        'activePage': 'email'
    }
    send_mail_template(settings.EMAIL_SUBJECT_EMAIL_CHANGED,
                       'emails/email_reset_complete_old_address_notification.txt', tvars, email_to=old_email)

    return render(request, 'accounts/email_reset_complete.html', tvars)



def problems_logging_in(request):
    """This view gets a User object from ProblemsLoggingInForm form contents and then either sends email instructions
    to re-activate the user (if the user is not active) or sends instructions to re-set the password (if the user
    is active).
    """
    if request.method == 'POST':
        form = ProblemsLoggingInForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username_or_email']
            try:
                user = User.objects.get(Q(email__iexact=username_or_email)\
                         | Q(username__iexact=username_or_email))
                if not user.is_active:
                    # If user is not activated, send instructions to re-activate the user
                    send_activation(user)
                else:
                    # If user is activated, send instructions to re-set the password (act as if the pre-BW password
                    # reset view was called)
                    # NOTE: we pass the same request.POST as we did to the ProblemsLoggingInForm. We can do that
                    # because both forms have the same fields.
                    pwd_reset_form = FsPasswordResetForm(request.POST)
                    if pwd_reset_form.is_valid():
                        pwd_reset_form.save(
                            subject_template_name='emails/password_reset_subject.txt',
                            email_template_name='emails/password_reset_email.html',
                            use_https=request.is_secure(),
                            request=request
                        )
            except User.DoesNotExist:
                pass

    # The view returns the same empty response regardless of whether an email was sent or not. This is to avoid
    # giving login credentials information to potential attackers.
    return JsonResponse({})


@login_required
@transaction.atomic()
def flag_user(request, username):
    if request.POST:
        flagged_user = User.objects.get(username__iexact=username)
        reporting_user = request.user
        object_id = request.POST["object_id"]
        if object_id:
            try:
                if request.POST["flag_type"] == "PM":
                    flagged_object = Message.objects.get(id=object_id, user_from=flagged_user)
                elif request.POST["flag_type"] == "FP":
                    flagged_object = Post.objects.get(id=object_id, author=flagged_user)
                elif request.POST["flag_type"] == "SC":
                    flagged_object = Comment.objects.get(id=object_id, user=flagged_user)
                else:
                    return HttpResponse(json.dumps({"errors": True}), content_type='application/javascript')
            except (Message.DoesNotExist, Post.DoesNotExist, Comment.DoesNotExist) as e:
                return HttpResponse(json.dumps({"errors": True}), content_type='application/javascript')
        else:
            return HttpResponse(json.dumps({"errors": True}), content_type='application/javascript')

        previous_reports_count = UserFlag.objects.filter(user=flagged_user)\
            .values('reporting_user').distinct().count()
        uflag = UserFlag(user=flagged_user, reporting_user=reporting_user, content_object=flagged_object)
        uflag.save()

        reports_count = UserFlag.objects.filter(user=flagged_user)\
            .values('reporting_user').distinct().count()
        if reports_count != previous_reports_count and \
                (reports_count == settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION or
                 reports_count == settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING):

            # Get all flagged objects by the user, create links to admin pages and send email
            flagged_objects = UserFlag.objects.filter(user=flagged_user)
            objects_data = []
            added_objects = []
            for f_object in flagged_objects:
                key = str(f_object.content_type) + str(f_object.object_id)
                if key not in added_objects:
                    added_objects.append(key)
                    try:
                        obj = f_object.content_type.get_object_for_this_type(id=f_object.object_id)
                        url = reverse('admin:%s_%s_change' %
                                      (obj._meta.app_label,  obj._meta.model_name), args=[obj.id])
                        if isinstance(obj, Comment):
                            content = obj.comment
                        elif isinstance(obj, Post):
                            content = obj.body
                        elif isinstance(obj, Message):
                            content = obj.body.body
                        else:
                            content = ''
                        objects_data.append([str(f_object.content_type), request.build_absolute_uri(url), content])
                    except ObjectDoesNotExist:
                        objects_data.append([str(f_object.content_type), "url not available", ""])
            user_url = reverse('admin:%s_%s_delete' %
                               (flagged_user._meta.app_label, flagged_user._meta.model_name), args=[flagged_user.id])
            user_url = request.build_absolute_uri(user_url)
            clear_url = reverse("clear-flags-user", args=[flagged_user.username])
            clear_url = request.build_absolute_uri(clear_url)
            if reports_count < settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING:
                template_to_use = 'emails/email_report_spammer_admins.txt'
            else:
                template_to_use = 'emails/email_report_blocked_spammer_admins.txt'

            tvars = {'flagged_user': flagged_user,
                     'objects_data': objects_data,
                     'user_url': user_url,
                     'clear_url': clear_url}
            send_mail_template_to_support(
                settings.EMAIL_SUBJECT_USER_SPAM_REPORT, template_to_use, tvars, extra_subject=flagged_user.username)
        return HttpResponse(json.dumps({"errors": None}), content_type='application/javascript')
    else:
        return HttpResponse(json.dumps({"errors": True}), content_type='application/javascript')


@login_required
def clear_flags_user(request, username):
    if request.user.is_superuser or request.user.is_staff:
        flags = UserFlag.objects.filter(user__username = username)
        num = len(flags)
        for flag in flags:
            flag.delete()
        messages.add_message(request, messages.INFO, f'{num} flag{"" if num == 1 else "s"} cleared for user {username}')
        return HttpResponseRedirect(reverse('account', args=[username]))
    else:
        return HttpResponseRedirect(reverse('login'))
