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

import datetime
import errno
import json
import logging
import os
import tempfile
import uuid
import cStringIO
import csv

import gearman
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Count, Q
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
from oauth2_provider.models import AccessToken

import tickets.views as TicketViews
import utils.sound_upload
from accounts.admin import DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from accounts.forms import EmailResetForm
from accounts.forms import UploadFileForm, FlashUploadFileForm, FileChoiceForm, RegistrationForm, ReactivationForm, \
    UsernameReminderForm, \
    ProfileForm, AvatarForm, TermsOfServiceForm, DeleteUserForm, EmailSettingsForm, BulkDescribeForm, UsernameField, \
    username_taken_by_other_user
from accounts.models import Profile, ResetEmailRequest, UserFlag, DeletedUser, UserDeletionRequest
from bookmarks.models import Bookmark
from comments.models import Comment
from follow import follow_utils
from forum.models import Post
from messages.models import Message
from sounds.forms import NewLicenseForm, PackForm, SoundDescriptionForm, GeotaggingForm
from sounds.models import Sound, Pack, Download, SoundLicenseHistory, BulkUploadProgress, PackDownload
from utils.cache import invalidate_template_cache
from utils.dbtime import DBTime
from utils.encryption import create_hash
from utils.filesystem import generate_tree, remove_directory_if_empty, create_directories
from utils.images import extract_square
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


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def crash_me(request):
    raise Exception


def login(request, template_name, authentication_form):
    # Freesound-specific login view to check if a user has multiple accounts
    # with the same email address. We can switch back to the regular django view
    # once all accounts are adapted
    response = LoginView.as_view(template_name=template_name, authentication_form=authentication_form)(request)
    if isinstance(response, HttpResponseRedirect):
        # If there is a redirect it's because the login was successful
        # Now we check if the logged in user has shared email problems
        if request.user.profile.has_shared_email():
            # If the logged in user has an email shared with other accounts, we redirect to the email update page
            redirect_url = reverse("accounts-multi-email-cleanup")
            next_param = request.POST.get('next', None)
            if next_param:
                redirect_url += '?next=%s' % next_param
            return HttpResponseRedirect(redirect_url)
        else:
            return response

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
        form = NewLicenseForm(request.POST)
        if form.is_valid():
            selected_license = form.cleaned_data['license']
            Sound.objects.filter(user=request.user).update(license=selected_license, is_index_dirty=True)
            for sound in Sound.objects.filter(user=request.user).all():
                SoundLicenseHistory.objects.create(sound=sound, license=selected_license)
            request.user.profile.has_old_license = False
            request.user.profile.save()
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = NewLicenseForm()
    tvars = {'form': form}
    return render(request, 'accounts/choose_new_license.html', tvars)


@login_required
def tos_acceptance(request):
    if request.method == 'POST':
        form = TermsOfServiceForm(request.POST)
        if form.is_valid():
            Profile.objects.filter(user=request.user).update(accepted_tos=True)
            cache.set('has-accepted-tos-%s' % request.user.id, 'yes', 2592000)
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = TermsOfServiceForm()
    tvars = {'form': form}
    return render(request, 'accounts/accept_terms_of_service.html', tvars)


@transaction.atomic()
def registration(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_activation(user)
            return render(request, 'accounts/registration_done.html')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/registration.html', {'form': form})


def activate_user(request, username, uid_hash):
    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return render(request, 'accounts/activate.html', {'user_does_not_exist': True})

    new_hash = create_hash(user.id)
    if new_hash != uid_hash:
        return render(request, 'accounts/activate.html', {'decode_error': True})

    user.is_active = True
    user.save()
    return render(request, 'accounts/activate.html', {'all_ok': True})


def send_activation(user):
    uid_hash = create_hash(user.id)
    username = user.username
    tvars = {
        'user': user,
        'username': username,
        'hash': uid_hash
    }
    send_mail_template(settings.EMAIL_SUBJECT_ACTIVATION_LINK, 'accounts/email_activation.txt', tvars, user_to=user)


def resend_activation(request):
    if request.method == 'POST':
        form = ReactivationForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['user']
            try:
                user = User.objects.get((Q(email__iexact=username_or_email)\
                         | Q(username__iexact=username_or_email))\
                         & Q(is_active=False))
                send_activation(user)
            except User.DoesNotExist:
                pass
            return render(request, 'accounts/resend_activation_done.html')
    else:
        form = ReactivationForm()

    return render(request, 'accounts/resend_activation.html', {'form': form})


def username_reminder(request):
    if request.method == 'POST':
        form = UsernameReminderForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['user']

            try:
                user = User.objects.get(email__iexact=email)
                send_mail_template(settings.EMAIL_SUBJECT_USERNAME_REMINDER, 'accounts/email_username_reminder.txt',
                                   {'user': user}, user_to=user)
            except User.DoesNotExist:
                pass

            return render(request, 'accounts/username_reminder.html', {'form': form, 'sent': True})
    else:
        form = UsernameReminderForm()

    return render(request, 'accounts/username_reminder.html', {'form': form, 'sent': False})


@login_required
def home(request):
    user = request.user

    # Tagcloud
    tags = user.profile.get_user_tags()

    # Sounds
    latest_sounds = Sound.objects.bulk_sounds_for_user(user_id=user.id, limit=5)
    unprocessed_sounds = Sound.objects.select_related().filter(user=user).exclude(processing_state="OK")
    unmoderated_sounds = TicketViews.get_pending_sounds(request.user)
    unmoderated_sounds_count = len(unmoderated_sounds)
    num_more_unmoderated_sounds = 0
    if unmoderated_sounds_count > settings.MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE:
        num_more_unmoderated_sounds = unmoderated_sounds_count - settings.MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE
        unmoderated_sounds = unmoderated_sounds[:settings.MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE]

    # Packs
    latest_packs = Pack.objects.select_related().filter(user=user, num_sounds__gt=0) \
                       .exclude(is_deleted=True).order_by("-last_updated")[0:5]
    packs_without_sounds = Pack.objects.select_related().filter(user=user, num_sounds=0).exclude(is_deleted=True)
    # 'packs_without_sounds' also includes packs that only contain unmoderated or unprocessed sounds

    # Moderation stats
    new_posts = 0
    if request.user.has_perm('forum.can_moderate_forum'):
        new_posts = Post.objects.filter(moderation_state='NM').count()

    # Followers
    following, followers, following_tags, following_count, followers_count, following_tags_count \
        = follow_utils.get_vars_for_home_view(user)

    current_bulkdescribe = BulkUploadProgress.objects.filter(user=user).exclude(progress_type="C")
    tvars = {
        'home': True,
        'latest_sounds': latest_sounds,
        'current_bulkdescribe': current_bulkdescribe,
        'unprocessed_sounds': unprocessed_sounds,
        'unmoderated_sounds': unmoderated_sounds,
        'unmoderated_sounds_count': unmoderated_sounds_count,
        'num_more_unmoderated_sounds': num_more_unmoderated_sounds,
        'latest_packs': latest_packs,
        'packs_without_sounds': packs_without_sounds,
        'new_posts': new_posts,
        'following': following,
        'followers': followers,
        'following_tags': following_tags,
        'following_count': following_count,
        'followers_count': followers_count,
        'following_tags_count': following_tags_count,
        'tags': tags,
    }
    return render(request, 'accounts/account.html', tvars)


@login_required
def edit_email_settings(request):
    if request.method == "POST":
        form = EmailSettingsForm(request.POST)
        if form.is_valid():
            email_type_ids = form.cleaned_data['email_types']
            request.user.profile.set_enabled_email_types(email_type_ids)
            messages.add_message(request, messages.INFO, 'Your email notification preferences have been updated')
            return HttpResponseRedirect(reverse("accounts-edit"))
    else:
        # Get list of enabled email_types
        all_emails = request.user.profile.get_enabled_email_types()
        form = EmailSettingsForm(initial={
            'email_types': all_emails,
            })
    tvars = {'form': form}
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
            invalidate_template_cache('user_header', request.user.id)

            profile.save()
            msg_txt = "Your profile has been updated correctly."
            if old_sound_signature != profile.sound_signature:
                msg_txt += " Please note that it might take some time until your sound signature is updated in all your sounds."
            messages.add_message(request, messages.INFO, msg_txt)
            return HttpResponseRedirect(reverse("accounts-home"))
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
            return HttpResponseRedirect(reverse("accounts-home"))
    else:
        image_form = AvatarForm(prefix="image")

    has_granted_permissions = AccessToken.objects.filter(user=request.user).count()

    tvars = {
        'profile': profile,
        'profile_form': profile_form,
        'image_form': image_form,
        'has_granted_permissions': has_granted_permissions
    }
    return render(request, 'accounts/edit.html', tvars)


@transaction.atomic()
def handle_uploaded_image(profile, f):
    upload_logger.info("\thandling profile image upload")
    create_directories(os.path.dirname(profile.locations("avatar.L.path")), exist_ok=True)

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
        upload_logger.error("\tfailed writing file error: %s", str(e))

    upload_logger.info("\tcreating thumbnails")
    path_s = profile.locations("avatar.S.path")
    path_m = profile.locations("avatar.M.path")
    path_l = profile.locations("avatar.L.path")
    try:
        extract_square(tmp_image_path, path_s, 32)
        upload_logger.info("\tcreated small thumbnail")
        profile.has_avatar = True
        profile.save()
    except Exception as e:
        upload_logger.error("\tfailed creating small thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_m, 40)
        upload_logger.info("\tcreated medium thumbnail")
    except Exception as e:
        upload_logger.error("\tfailed creating medium thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_l, 70)
        upload_logger.info("\tcreated large thumbnail")
    except Exception as e:
        upload_logger.error("\tfailed creating large thumbnails: " + str(e))

    copy_avatar_to_mirror_locations(profile)
    os.unlink(tmp_image_path)


@login_required
def describe(request):
    file_structure, files = generate_tree(request.user.profile.locations()['uploads_dir'])
    file_structure.name = ''

    if request.method == 'POST':
        form = FileChoiceForm(files, request.POST, prefix='sound')
        csv_form = BulkDescribeForm(request.POST, request.FILES, prefix='bulk')
        if csv_form.is_valid():
            directory = os.path.join(settings.CSV_PATH, str(request.user.id))
            create_directories(directory, exist_ok=True)

            extension = csv_form.cleaned_data['csv_file'].name.rsplit('.', 1)[-1].lower()
            path = os.path.join(directory, str(uuid.uuid4()) + '.%s' % extension)
            destination = open(path, 'wb')

            f = csv_form.cleaned_data['csv_file']
            for chunk in f.chunks():
                destination.write(chunk)

            bulk = BulkUploadProgress.objects.create(user=request.user, csv_path=path, original_csv_filename=f.name)
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("validate_bulk_describe_csv", str(bulk.id), wait_until_complete=False, background=True)
            return HttpResponseRedirect(reverse("accounts-bulk-describe", args=[bulk.id]))
        elif form.is_valid():
            if "delete" in request.POST:
                filenames = [files[x].name for x in form.cleaned_data["files"]]
                tvars = {'form': form, 'filenames': filenames}
                return render(request, 'accounts/confirm_delete_undescribed_files.html', tvars)
            elif "delete_confirm" in request.POST:
                for f in form.cleaned_data["files"]:
                    try:
                        os.remove(files[f].full_path)
                        remove_uploaded_file_from_mirror_locations(files[f].full_path)
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            upload_logger.error("Failed to remove file %s", str(e))
                        else:
                            raise

                # Remove user uploads directory if there are no more files to describe
                user_uploads_dir = request.user.profile.locations()['uploads_dir']
                remove_directory_if_empty(user_uploads_dir)
                remove_empty_user_directory_from_mirror_locations(user_uploads_dir)

                return HttpResponseRedirect(reverse('accounts-describe'))
            elif "describe" in request.POST:
                # Clear existing describe-related session data
                for key in ['describe_sounds', 'describe_license', 'describe_pack']:
                    request.session.pop(key, None)  # Clear pre-existing describe-sound related data in session
                request.session['describe_sounds'] = [files[x] for x in form.cleaned_data["files"]]
                # If only one file is choosen, go straight to the last step of the describe process,
                # otherwise go to license selection step
                if len(request.session['describe_sounds']) > 1:
                    return HttpResponseRedirect(reverse('accounts-describe-license'))
                else:
                    return HttpResponseRedirect(reverse('accounts-describe-sounds'))
            else:
                form = FileChoiceForm(files)
                tvars = {'form': form, 'file_structure': file_structure}
                return render(request, 'accounts/describe.html', tvars)
    else:
        csv_form = BulkDescribeForm(prefix='bulk')
        form = FileChoiceForm(files, prefix='sound')
    tvars = {'form': form, 'file_structure': file_structure, 'n_files': len(files), 'csv_form': csv_form}
    return render(request, 'accounts/describe.html', tvars)


@login_required
def describe_license(request):
    if request.method == 'POST':
        form = NewLicenseForm(request.POST)
        if form.is_valid():
            request.session['describe_license'] = form.cleaned_data['license']
            return HttpResponseRedirect(reverse('accounts-describe-pack'))
    else:
        form = NewLicenseForm()
    tvars = {'form': form}
    return render(request, 'accounts/describe_license.html', tvars)


@login_required
def describe_pack(request):
    packs = Pack.objects.filter(user=request.user).exclude(is_deleted=True)
    if request.method == 'POST':
        form = PackForm(packs, request.POST, prefix="pack")
        if form.is_valid():
            data = form.cleaned_data
            if data['new_pack']:
                pack, created = Pack.objects.get_or_create(user=request.user, name=data['new_pack'])
                request.session['describe_pack'] = pack
            elif data['pack']:
                request.session['describe_pack'] = data['pack']
            else:
                request.session['describe_pack'] = False
            return HttpResponseRedirect(reverse('accounts-describe-sounds'))
    else:
        form = PackForm(packs, prefix="pack")
    tvars = {'form': form}
    return render(request, 'accounts/describe_pack.html', tvars)


@login_required
def describe_sounds(request):
    forms = []
    sounds_to_process = []
    sounds = request.session.get('describe_sounds', False)
    if not sounds:
        msg = 'Please pick at least one sound.'
        messages.add_message(request, messages.WARNING, msg)
        return HttpResponseRedirect(reverse('accounts-describe'))
    sounds_to_describe = sounds[0:settings.SOUNDS_PER_DESCRIBE_ROUND]
    request.session['describe_sounds_number'] = len(request.session.get('describe_sounds'))
    selected_license = request.session.get('describe_license', False)
    selected_pack = request.session.get('describe_pack', False)

    # If there are no files in the session redirect to the first describe page
    if len(sounds_to_describe) <= 0:
        msg = 'You have finished describing your sounds.'
        messages.add_message(request, messages.WARNING, msg)
        return HttpResponseRedirect(reverse('accounts-describe'))

    tvars = {
        'sounds_per_round': settings.SOUNDS_PER_DESCRIBE_ROUND,
        'forms': forms,
        'last_latlong': request.user.profile.get_last_latlong(),
    }

    if request.method == 'POST':
        # First get all the data
        n_sounds_already_part_of_freesound = 0
        for i in range(len(sounds_to_describe)):
            prefix = str(i)
            forms.append({})
            forms[i]['sound'] = sounds_to_describe[i]
            forms[i]['description'] = SoundDescriptionForm(request.POST, prefix=prefix, explicit_disable=False)
            forms[i]['geotag'] = GeotaggingForm(request.POST, prefix=prefix)
            forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user).exclude(is_deleted=True),
                                        request.POST,
                                        prefix=prefix)
            forms[i]['license'] = NewLicenseForm(request.POST, prefix=prefix)
        # Validate each form
        for i in range(len(sounds_to_describe)):
            for f in ['license', 'geotag', 'pack', 'description']:
                if not forms[i][f].is_valid():
                    # If at least one form is not valid, render template with form errors
                    return render(request, 'accounts/describe_sounds.html', tvars)

        # All valid, then create sounds and moderation tickets
        dirty_packs = []
        for i in range(len(sounds_to_describe)):
            sound_fields = {
                'name': forms[i]['description'].cleaned_data['name'],
                'dest_path': forms[i]['sound'].full_path,
                'license': forms[i]['license'].cleaned_data['license'],
                'description': forms[i]['description'].cleaned_data.get('description', ''),
                'tags': forms[i]['description'].cleaned_data.get('tags', ''),
                'is_explicit': forms[i]['description'].cleaned_data['is_explicit'],
            }

            pack = forms[i]['pack'].cleaned_data.get('pack', False)
            new_pack = forms[i]['pack'].cleaned_data.get('new_pack', False)
            if not pack and new_pack:
                sound_fields['pack'] = new_pack
            elif pack:
                sound_fields['pack'] = pack

            data = forms[i]['geotag'].cleaned_data
            if not data.get('remove_geotag') and data.get('lat'):  # if 'lat' is in data, we assume other fields are too
                geotag = '%s,%s,%d' % (data.get('lat'), data.get('lon'), data.get('zoom'))
                sound_fields['geotag'] = geotag

            try:
                user = request.user
                sound = utils.sound_upload.create_sound(user, sound_fields, process=False)
                sounds_to_process.append(sound)
                if user.profile.is_whitelisted:
                    messages.add_message(request, messages.INFO,
                        'File <a href="%s">%s</a> has been described and has been added to freesound.' % \
                        (sound.get_absolute_url(), sound.original_filename))
                else:
                    messages.add_message(request, messages.INFO,
                        'File <a href="%s">%s</a> has been described and is now awaiting processing '
                        'and moderation.' % (sound.get_absolute_url(), sound.original_filename))

                    # Invalidate affected caches in user header
                    invalidate_template_cache("user_header", request.user.id)
                    for moderator in Group.objects.get(name='moderators').user_set.all():
                        invalidate_template_cache("user_header", moderator.id)

            except utils.sound_upload.NoAudioException:
                # If for some reason audio file does not exist, skip creating this sound
                messages.add_message(request, messages.ERROR,
                                     'Something went wrong with accessing the file %s.' % forms[i]['description'].cleaned_data['name'])
            except utils.sound_upload.AlreadyExistsException as e:
                msg = e.message
                messages.add_message(request, messages.WARNING, msg)
            except utils.sound_upload.CantMoveException as e:
                upload_logger.error(e.message, e)

        # Remove the files we just described from the session and redirect to this page
        request.session['describe_sounds'] = request.session['describe_sounds'][len(sounds_to_describe):]

        # Process sounds and packs
        # N.B. we do this at the end to avoid conflicts between django-web and django-workers
        # If we're not careful django's save() functions will overwrite any processing we
        # do on the workers.
        # In the future if django-workers do not write to the db this might be changed
        try:
            for s in sounds_to_process:
                s.process_and_analyze(high_priority=True)
        except Exception as e:
            sounds_logger.error('Sound with id %s could not be scheduled. (%s)' % (s.id, str(e)))
        for p in dirty_packs:
            p.process()

        # Check if all sounds have been described after that round and redirect accordingly
        if len(request.session['describe_sounds']) <= 0:
            if len(sounds_to_describe) != n_sounds_already_part_of_freesound:
                msg = 'You have described all the selected files and are now awaiting processing and moderation. ' \
                      'You can check the status of your uploaded sounds in your <a href="%s">home page</a>. ' \
                      'Once your sounds have been processed, you can also get information about the moderation ' \
                      'status in the <a href="%s">uploaded sounds awaiting moderation' \
                      '</a> page.' % (reverse('accounts-home'), reverse('accounts-pending'))
                messages.add_message(request, messages.WARNING, msg)
            return HttpResponseRedirect(reverse('accounts-describe'))
        else:
            return HttpResponseRedirect(reverse('accounts-describe-sounds'))
    else:
        for i in range(len(sounds_to_describe)):
            prefix = str(i)
            forms.append({})
            forms[i]['sound'] = sounds_to_describe[i]
            forms[i]['description'] = SoundDescriptionForm(initial={'name': forms[i]['sound'].name}, prefix=prefix)
            forms[i]['geotag'] = GeotaggingForm(prefix=prefix)
            if selected_pack:
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user).exclude(is_deleted=True),
                                            prefix=prefix,
                                            initial={'pack': selected_pack.id})
            else:
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user).exclude(is_deleted=True),
                                            prefix=prefix)
            if selected_license:
                forms[i]['license'] = NewLicenseForm(initial={'license': selected_license},
                                                     prefix=prefix)
            else:
                forms[i]['license'] = NewLicenseForm(prefix=prefix)

    return render(request, 'accounts/describe_sounds.html', tvars)


@login_required
def attribution(request):
    qs_sounds = Download.objects.annotate(download_type=Value("sound", CharField()))\
        .values('download_type', 'sound_id', 'sound__user__username', 'sound__original_filename',
                'license__name', 'sound__license__name', 'created').filter(user=request.user)
    qs_packs = PackDownload.objects.annotate(download_type=Value("pack", CharField()))\
        .values('download_type', 'pack_id', 'pack__user__username', 'pack__name', 'pack__name',
                'pack__name', 'created').filter(user=request.user)
    # NOTE: in the query above we duplciate 'pack__name' so that qs_packs has same num columns than qs_sounds. This is
    # a requirement for doing QuerySet.union below. Also as a result of using QuerySet.union, the names of the columns
    # (keys in each dictionary element) are unified and taken from the main query set. This means that after the union,
    # queryset entries corresponding to PackDownload will have corresponding field names from entries corresponding to
    # Download. Therefre to access the pack_id (which is the second value in the list), you'll need to do
    # item['sound_id'] instead of item ['pack_id']. See the template of this view for an example of this.
    qs = qs_sounds.union(qs_packs).order_by('-created')

    tvars = {'format': request.GET.get("format", "regular")}
    tvars.update(paginate(request, qs, 40))
    return render(request, 'accounts/attribution.html', tvars)


@login_required
def download_attribution(request):
    content = {'csv': 'csv', 'txt': 'plain'}

    qs_sounds = Download.objects.annotate(download_type=Value('sound', CharField()))\
        .values('download_type', 'sound_id', 'sound__user__username', 'sound__original_filename',
                'license__name', 'sound__license__name', 'created').filter(user=request.user)
    qs_packs = PackDownload.objects.annotate(download_type=Value('pack', CharField()))\
        .values('download_type', 'pack_id', 'pack__user__username', 'pack__name', 'pack__name',
                'pack__name', 'created').filter(user=request.user)
    # NOTE: see the above view, attribution.
    qs = qs_sounds.union(qs_packs).order_by('-created')

    download = request.GET.get('dl', '')
    if download in ['csv', 'txt']:
        now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = '%s_%s_attribution.%s' % (request.user, now, download)
        response = HttpResponse(content_type='text/%s' % content[download])
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        output = cStringIO.StringIO()
        if download == 'csv':
            output.write('Download Type,File Name,User,License\r\n')
            csv_writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for row in qs:
                csv_writer.writerow([row['download_type'][0].upper(), row['sound__original_filename'],
                                    row['sound__user__username'], row['license__name'] or row['sound__license__name']])
        elif download == 'txt':
            for row in qs:
                output.write("%s: %s by %s | License: %s\n" % (row['download_type'][0].upper(),
                             row['sound__original_filename'], row['sound__user__username'],
                             row['license__name'] or row['sound__license__name']))
        response.writelines(output.getvalue())
        return response
    else:
        return HttpResponseRedirect(reverse('accounts-attribution'))


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def downloaded_sounds(request, username):
    user = request.parameter_user
    qs = Download.objects.filter(user_id=user.id)
    paginator = paginate(request, qs, settings.SOUNDS_PER_PAGE, object_count=user.profile.num_sound_downloads)
    page = paginator["page"]
    sound_ids = [d.sound_id for d in page]
    sounds = Sound.objects.ordered_ids(sound_ids)
    tvars = {"username": username,
             "user": user,
             "sounds": sounds}
    tvars.update(paginator)
    return render(request, 'accounts/downloaded_sounds.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def downloaded_packs(request, username):
    user = request.parameter_user
    qs = PackDownload.objects.filter(user=user.id)
    paginator = paginate(request, qs, settings.PACKS_PER_PAGE, object_count=user.profile.num_pack_downloads)
    page = paginator["page"]
    pack_ids = [d.pack_id for d in page]
    packs = Pack.objects.ordered_ids(pack_ids)
    tvars = {"username": username,
             "packs": packs}
    tvars.update(paginator)
    return render(request, 'accounts/downloaded_packs.html', tvars)


def latest_content_type(scores):
    if scores['uploads'] >= scores['posts'] and scores['uploads'] >= scores['comments']:
        return 'sound'
    elif scores['posts'] >= scores['uploads'] and scores['posts'] > scores['comments']:
        return 'post'
    elif scores['comments'] >= scores['uploads'] and scores['comments'] > scores['posts']:
        return 'comment'


def create_user_rank(uploaders, posters, commenters):
    upload_weight = 1
    post_weight = 0.7
    comment_weight = 0.0
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
    num_days = 14
    num_active_users = 10
    num_all_time_active_users = 10
    last_time = DBTime.get_last_time() - datetime.timedelta(num_days)

    # Most active users in last num_days, newest active users in last num_days and logged in users
    latest_uploaders = Sound.public.filter(created__gte=last_time).values("user").annotate(Count('id'))\
        .order_by("-id__count")
    latest_posters = Post.objects.filter(created__gte=last_time).values("author_id").annotate(Count('id'))\
        .order_by("-id__count")
    latest_commenters = Comment.objects.filter(created__gte=last_time).values("user_id").annotate(Count('id'))\
        .order_by("-id__count")
    user_rank, sort_list = create_user_rank(latest_uploaders, latest_posters, latest_commenters)
    most_active_users = User.objects.select_related("profile")\
        .filter(id__in=[u[1] for u in sorted(sort_list, reverse=True)[:num_active_users]])
    new_users = User.objects.select_related("profile").filter(date_joined__gte=last_time)\
        .filter(id__in=user_rank.keys()).order_by('-date_joined')[:num_active_users+5]
    logged_users = User.objects.select_related("profile").filter(id__in=get_online_users())
    most_active_users_display = [[u, latest_content_type(user_rank[u.id]), user_rank[u.id]] for u in most_active_users]
    most_active_users_display = sorted(most_active_users_display,
                                       key=lambda usr: user_rank[usr[0].id]['score'],
                                       reverse=True)
    new_users_display = [[u, latest_content_type(user_rank[u.id]), user_rank[u.id]] for u in new_users]

    # All time most active users (these queries are kind of slow, but page is cached)
    all_time_uploaders = Profile.objects.extra(select={'id__count': 'num_sounds'})\
        .order_by("-num_sounds").values("user", "id__count")[:num_all_time_active_users]
    all_time_posters = Profile.objects.extra(select={'id__count': 'num_posts', 'author_id': 'user_id'})\
        .order_by("-num_posts").values("author_id", "id__count")[:num_all_time_active_users]
    # Performing a count(*) on Comment table is slow, we could add 'num_comments' to user profile
    all_time_commenters = Comment.objects.all().values("user_id").annotate(Count('id'))\
        .order_by("-id__count")[:num_all_time_active_users]
    all_time_user_rank, all_time_sort_list = create_user_rank(all_time_uploaders, all_time_posters, all_time_commenters)
    all_time_most_active_users = User.objects.select_related("profile")\
        .filter(id__in=[u[1] for u in sorted(all_time_sort_list, reverse=True)[:num_all_time_active_users]])
    all_time_most_active_users_display = [[u, all_time_user_rank[u.id]] for u in all_time_most_active_users]
    all_time_most_active_users_display = sorted(all_time_most_active_users_display,
                                                key=lambda usr: all_time_user_rank[usr[0].id]['score'],
                                                reverse=True)

    tvars = {
        'num_days': num_days,
        'most_active_users': most_active_users_display,
        'all_time_most_active_users': all_time_most_active_users_display,
        'new_users': new_users_display,
        'logged_users': logged_users,
    }
    return render(request, 'accounts/accounts.html', tvars)


@redirect_if_old_username_or_404
def account(request, username):
    user = request.parameter_user

    tags = user.profile.get_user_tags() if user.profile else []
    latest_sounds = list(Sound.objects.bulk_sounds_for_user(user.id, settings.SOUNDS_PER_PAGE))
    latest_packs = Pack.objects.select_related().filter(user=user, num_sounds__gt=0).exclude(is_deleted=True) \
                                .order_by("-last_updated")[0:10]
    following, followers, following_tags, following_count, followers_count, following_tags_count = \
        follow_utils.get_vars_for_account_view(user)
    follow_user_url = reverse('follow-user', args=[username])
    unfollow_user_url = reverse('unfollow-user', args=[username])
    show_unfollow_button = request.user.is_authenticated and follow_utils.is_user_following_user(request.user, user)
    has_bookmarks = Bookmark.objects.filter(user=user).exists()
    if not user.is_active:
        messages.add_message(request, messages.INFO, 'This account has <b>not been activated</b> yet.')
    if request.user.has_perm('tickets.can_moderate'):
        num_sounds_pending_count = user.profile.num_sounds_pending_moderation()
    else:
        num_sounds_pending_count = None

    show_about = ((request.user == user)  # user is looking at own page
                  or request.user.is_superuser  # admins should always see about fields
                  or user.is_superuser  # no reason to hide admin's about fields
                  or user.profile.get_total_downloads > 0  # user has downloads
                  or user.profile.num_sounds > 0)  # user has uploads

    tvars = {
        'home': False,
        'user': user,
        'tags': tags,
        'latest_sounds': latest_sounds,
        'latest_packs': latest_packs,
        'following': following,
        'followers': followers,
        'following_tags': following_tags,
        'following_count': following_count,
        'followers_count': followers_count,
        'following_tags_count': following_tags_count,
        'follow_user_url': follow_user_url,
        'unfollow_user_url': unfollow_user_url,
        'show_unfollow_button': show_unfollow_button,
        'has_bookmarks': has_bookmarks,
        'num_sounds_pending_count': num_sounds_pending_count,
        'show_about': show_about,
    }
    return render(request, 'accounts/account.html', tvars)


def handle_uploaded_file(user_id, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.UPLOADS_PATH, str(user_id))
    upload_logger.info("\thandling file upload")
    create_directories(directory, exist_ok=True)
    path = os.path.join(directory, os.path.basename(f.name))
    try:
        upload_logger.info("\topening file: %s", path)
        destination = open(path.encode("utf-8"), 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        upload_logger.info("file upload done")
        copy_uploaded_file_to_mirror_locations(path)
    except Exception as e:
        upload_logger.warning("failed writing file error: %s", str(e))
        return False
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
                for file_ in submitted_files:
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
        'max_file_size_in_MB': int(round(settings.UPLOAD_MAX_FILE_SIZE_COMBINED * 1.0 / (1024 * 1024)))
    }
    return render(request, 'accounts/upload.html', tvars)


@login_required
def bulk_describe(request, bulk_id):
    if not request.user.profile.can_do_bulk_upload():
        messages.add_message(request, messages.INFO, "Your user does not have permission to use the bulk describe "
                                                     "feature. You must upload at least %i sounds before being able"
                                                     "to use that feature." % settings.BULK_UPLOAD_MIN_SOUNDS)
        return HttpResponseRedirect(reverse('accounts-home'))

    bulk = get_object_or_404(BulkUploadProgress, id=int(bulk_id), user=request.user)

    if request.GET.get('action', False) == 'start' and bulk.progress_type == 'V':
        # If action is "start" and CSV is validated, mark BulkUploadProgress as "stared" and start describing sounds
        bulk.progress_type = 'S'
        bulk.save()
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        gm_client.submit_job("bulk_describe", str(bulk.id), wait_until_complete=False, background=True)

    elif request.GET.get('action', False) == 'delete' and bulk.progress_type in ['N', 'V']:
        # If action is "delete", delete BulkUploadProgress object and go back to describe page
        bulk.delete()
        return HttpResponseRedirect(reverse('accounts-describe'))

    elif request.GET.get('action', False) == 'close':
        # If action is "close", set the BulkUploadProgress object to closed state and redirect to home
        bulk.progress_type = 'C'
        bulk.save()
        return HttpResponseRedirect(reverse('accounts-home'))

    # Get progress info to be display if sound descirption process has started
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
            delete_sounds =\
                form.cleaned_data['delete_sounds'] == 'delete_sounds'
            delete_action = DELETE_USER_DELETE_SOUNDS_ACTION_NAME if delete_sounds \
                else DELETE_USER_KEEP_SOUNDS_ACTION_NAME
            delete_reason = DeletedUser.DELETION_REASON_SELF_DELETED
            web_logger.info('Requested async deletion of user {0} - {1}'.format(request.user.id, delete_action))

            # Submit deletion job to gearman so the user is deleted asynchronously
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_job("delete_user",
                                 json.dumps({'user_id': request.user.id, 'action': delete_action,
                                             'deletion_reason': delete_reason}),
                                 wait_until_complete=False, background=True)

            # Create a UserDeletionRequest with a status of 'Deletion action was triggered'
            UserDeletionRequest.objects.create(user=request.user,
                                               status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
                                               triggered_deletion_action=delete_action,
                                               triggered_deletion_reason=delete_reason)

            # Show a message to the user that the account will be deleted shortly
            messages.add_message(request, messages.INFO,
                                 'Your user account will be deleted in a few moments. Note that this process could '
                                 'take up to an hour for users with many uploaded sounds.')

            # NOTE: we used to do logout here because the user account was deleted synchronously. However now we don't
            # do this as the user is deleted asynchronously and we want to show the message that the user will be
            # deleted soon
            return HttpResponseRedirect(reverse("front-page"))
    else:
        form = DeleteUserForm(user_id=request.user.id)

    tvars = {
            'delete_form': form,
            'num_sounds': num_sounds,
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
        form = EmailResetForm(request.POST, user=request.user)
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
                    'token': default_token_generator.make_token(user),
                }
                send_mail_template(settings.EMAIL_SUBJECT_EMAIL_CHANGED,
                                   'accounts/email_reset_email.txt', tvars,
                                   email_to=email)

            return HttpResponseRedirect(reverse('accounts-email-reset-done'))
    else:
        form = EmailResetForm(user=request.user)
    tvars = {'form': form, 'user': request.user}
    return render(request, 'accounts/email_reset_form.html', tvars)


def email_reset_done(request):
    return render(request, 'accounts/email_reset_done.html')


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
    tvars = {'old_email': old_email, 'user': user}
    send_mail_template(settings.EMAIL_SUBJECT_EMAIL_CHANGED,
                       'accounts/email_reset_complete_old_address_notification.txt', tvars, email_to=old_email)

    return render(request, 'accounts/email_reset_complete.html', tvars)


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
                template_to_use = 'accounts/report_spammer_admins.txt'
            else:
                template_to_use = 'accounts/report_blocked_spammer_admins.txt'

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
        tvars = {'num': num, 'username': username}
        return render(request, 'accounts/flags_cleared.html', tvars)
    else:
        return HttpResponseRedirect(reverse('accounts-login'))


@login_required
def pending(request):
    user = request.user
    tickets_sounds = TicketViews.get_pending_sounds(user)
    pendings = []
    for ticket, sound in tickets_sounds:
        last_comments = ticket.get_n_last_non_moderator_only_comments(3)
        pendings.append((ticket, sound, last_comments))
    show_pagination = len(pendings) > settings.SOUNDS_PENDING_MODERATION_PER_PAGE
    n_unprocessed_sounds = Sound.objects.select_related().filter(user=user).exclude(processing_state="OK").count()
    if n_unprocessed_sounds:
        messages.add_message(request, messages.WARNING,
                             '%i of your recently uploaded sounds are still in processing' % n_unprocessed_sounds)
    moderators_version = False
    tvars = {
        'user': user,
        'show_pagination': show_pagination,
        'moderators_version': moderators_version,
        'own_page': True,
    }
    tvars.update(paginate(request, pendings, settings.SOUNDS_PENDING_MODERATION_PER_PAGE))
    return render(request, 'accounts/pending.html', tvars)
