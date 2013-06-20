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

import datetime, logging, os, tempfile, uuid, shutil, hashlib, base64
from accounts.forms import UploadFileForm, FileChoiceForm, RegistrationForm, \
    ReactivationForm, UsernameReminderForm, ProfileForm, AvatarForm, TermsOfServiceForm
from accounts.models import Profile, ResetEmailRequest, UserFlag
from comments.models import Comment
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseBadRequest, HttpResponseNotFound, Http404, \
    HttpResponsePermanentRedirect, HttpResponseServerError, HttpRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from forum.models import Post
from operator import itemgetter
from sounds.models import Sound, Pack, Download, License
from sounds.forms import NewLicenseForm, PackForm, SoundDescriptionForm, GeotaggingForm, RemixForm
from utils.dbtime import DBTime
from utils.onlineusers import get_online_users
from utils.encryption import decrypt, encrypt, create_hash
from utils.filesystem import generate_tree, md5file
from utils.functional import combine_dicts
from utils.images import extract_square
from utils.pagination import paginate
from utils.text import slugify
from geotags.models import GeoTag
from django.contrib import messages
from settings import SOUNDS_PER_DESCRIBE_ROUND
from tickets.models import Ticket, Queue, LinkedContent, TicketComment
from tickets import QUEUE_SOUND_MODERATION, TICKET_SOURCE_NEW_SOUND, \
    TICKET_STATUS_NEW
from utils.audioprocessing import get_sound_type
from django.core.cache import cache
import django.contrib.auth.views as authviews
from django.contrib.auth.forms import AuthenticationForm
from tickets.views import new_sound_tickets_count, new_support_tickets_count
from django.contrib.auth.tokens import default_token_generator
from accounts.forms import EmailResetForm
from django.views.decorators.cache import never_cache
from django.utils.http import base36_to_int
from django.template import loader
from django.utils.http import int_to_base36
from django.contrib.sites.models import get_current_site
from utils.mail import send_mail, send_mail_template
from django.db import transaction
from bookmarks.models import Bookmark
from django.contrib.auth.decorators import user_passes_test
import json
from messages.models import Message
from django.contrib.contenttypes.models import ContentType


audio_logger = logging.getLogger('audio')

@login_required
@user_passes_test(lambda u: u.is_staff, login_url = "/")
def crash_me(request):
    raise Exception


@login_required
def bulk_license_change(request):
    if request.method == 'POST':
        form = NewLicenseForm(request.POST)
        if form.is_valid():
            license = form.cleaned_data['license']
            Sound.objects.filter(user=request.user).update(license=license, is_index_dirty=True)
            
            # update old license flag
            Profile.objects.filter(user=request.user).update(has_old_license=False)
            # update cache
            cache.set("has-old-license-%s" % request.user.id, [False,Sound.objects.filter(user=request.user).exists()], 2592000)
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = NewLicenseForm()
    return render_to_response('accounts/choose_new_license.html', locals(), context_instance=RequestContext(request))

@login_required
def tos_acceptance(request):
    if request.method == 'POST':
        form = TermsOfServiceForm(request.POST)
        if form.is_valid():
            # update accepted tos field in user profile
            Profile.objects.filter(user=request.user).update(accepted_tos=True)
            # update cache
            cache.set("has-accepted-tos-%s" % request.user.id, 'yes', 2592000)
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = TermsOfServiceForm()
    return render_to_response('accounts/accept_terms_of_service.html', locals(), context_instance=RequestContext(request))



def activate_user(request, activation_key, username):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    try:
        user_id = decrypt(activation_key)
        user = User.objects.get(id=int(user_id))
        user.is_active = True
        user.save()
        return render_to_response('accounts/activate.html', { 'all_ok': True }, context_instance=RequestContext(request))
    except User.DoesNotExist: #@UndefinedVariable
        return render_to_response('accounts/activate.html', { 'user_does_not_exist': True }, context_instance=RequestContext(request))
    except TypeError, ValueError:
        return render_to_response('accounts/activate.html', { 'decode_error': True }, context_instance=RequestContext(request))

def activate_user2(request, username, hash):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist: #@UndefinedVariable
        return render_to_response('accounts/activate.html', { 'user_does_not_exist': True }, context_instance=RequestContext(request))

    new_hash = create_hash(user.id)
    if new_hash != hash:
        return render_to_response('accounts/activate.html', { 'decode_error': True }, context_instance=RequestContext(request))
    user.is_active = True
    user.save()
    
    return render_to_response('accounts/activate.html', { 'all_ok': True }, context_instance=RequestContext(request))

def send_activation(user):
    encrypted_user_id = encrypt(str(user.id))
    username = user.username
    send_mail_template(u'activation link.', 'accounts/email_activation.txt', locals(), None, user.email)

def send_activation2(user):
    hash = create_hash(user.id)
    username = user.username
    send_mail_template(u'activation link.', 'accounts/email_activation2.txt', locals(), None, user.email)

def registration(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    if request.method == "POST":
        form = RegistrationForm(request, request.POST)
        if form.is_valid():
            user = form.save()
            send_activation2(user)
            return render_to_response('accounts/registration_done.html', locals(), context_instance=RequestContext(request))
    else:
        form = RegistrationForm(request)

    return render_to_response('accounts/registration.html', locals(), context_instance=RequestContext(request))


def resend_activation(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    if request.method == "POST":
        form = ReactivationForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            send_activation2(user)
            return render_to_response('accounts/registration_done.html', locals(), context_instance=RequestContext(request))
    else:
        form = ReactivationForm()

    return render_to_response('accounts/resend_activation.html', locals(), context_instance=RequestContext(request))


def username_reminder(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    if request.method == "POST":
        form = UsernameReminderForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            send_mail_template(u'username reminder.', 'accounts/email_username_reminder.txt', dict(user=user), None, user.email)

            return render_to_response('accounts/username_reminder.html', dict(form=form, sent=True), context_instance=RequestContext(request))
    else:
        form = UsernameReminderForm()

    return render_to_response('accounts/username_reminder.html', dict(form=form, sent=False), context_instance=RequestContext(request))


@login_required
def home(request):
    user = request.user
    # expand tags because we will definitely be executing, and otherwise tags is called multiple times
    tags = list(user.profile.get_tagcloud())
    latest_sounds = Sound.objects.select_related().filter(user=user,processing_state="OK",moderation_state="OK")[0:5]
    unprocessed_sounds = Sound.objects.select_related().filter(user=user).exclude(processing_state="OK")
    unmoderated_sounds = Sound.objects.select_related().filter(user=user,processing_state="OK").exclude(moderation_state="OK")

    
    latest_packs = Pack.objects.select_related().filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:5]
    unmoderated_packs = Pack.objects.select_related().filter(user=user).exclude(sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:5]
    packs_without_sounds = Pack.objects.select_related().filter(user=user).annotate(num_sounds=Count('sound')).filter(num_sounds=0)
    
    # TODO: refactor: This list of geotags is only used to determine if we need to show the geotag map or not
    latest_geotags = Sound.public.filter(user=user).exclude(geotag=None)[0:10].exists()
    google_api_key = settings.GOOGLE_API_KEY
    home = True
    if home and request.user.has_perm('tickets.can_moderate'):
        new_sounds = new_sound_tickets_count()
        new_support = new_support_tickets_count()
    if home and request.user.has_perm('forum.can_moderate_forum'):
        new_posts = Post.objects.filter(moderation_state='NM').count()

    return render_to_response('accounts/account.html', locals(), context_instance=RequestContext(request))


def handle_uploaded_image(profile, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    logger.info("\thandling profile image upload")
    try:
        os.mkdir(os.path.dirname(profile.locations("avatar.L.path")))
    except:
        logger.info("\tfailed creating directory, probably already exist")
        pass

    ext = os.path.splitext(os.path.basename(f.name))[1]
    tmp_image_path = tempfile.mktemp(suffix=ext, prefix=str(profile.user.id))

    try:
        logger.info("\topening file: %s", tmp_image_path)
        destination = open(tmp_image_path, 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
        logger.info("\tfile upload done")
    except Exception, e:
        logger.error("\tfailed writing file error: %s", str(e))

    path_s = profile.locations("avatar.S.path")
    path_m = profile.locations("avatar.M.path")
    path_l = profile.locations("avatar.L.path")

    logger.info("\tcreating thumbnails")
    try:
        extract_square(tmp_image_path, path_s, 32)
        profile.has_avatar = True
        profile.save()
    except Exception, e:
        logger.error("\tfailed creating small thumbnails: " + str(e))

    logger.info("\tcreated small thumbnail")

    try:
        extract_square(tmp_image_path, path_m, 40)
    except Exception, e:
        logger.error("\tfailed creating medium thumbnails: " + str(e))

    try:
        extract_square(tmp_image_path, path_l, 70)
    except Exception, e:
        logger.error("\tfailed creating large thumbnails: " + str(e))

    logger.info("\tcreated medium thumbnail")

    os.unlink(tmp_image_path)


@login_required
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
        if profile_form.is_valid():
            profile_form.save()
            return HttpResponseRedirect(reverse("accounts-home"))
    else:
        profile_form = ProfileForm(request,instance=profile, prefix="profile")

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

    return render_to_response('accounts/edit.html', dict(profile=profile, profile_form=profile_form, image_form=image_form), context_instance=RequestContext(request))


@login_required
def describe(request):

    file_structure, files = generate_tree(os.path.join(settings.UPLOADS_PATH, str(request.user.id)))
    file_structure.name = 'Your uploaded files'

    if request.method == 'POST':
        form = FileChoiceForm(files, request.POST)
        
        if form.is_valid():
            if "delete" in request.POST: # If delete button is pressed
                filenames = [files[x].name for x in form.cleaned_data["files"]]
                return render_to_response('accounts/confirm_delete_undescribed_files.html', locals(), context_instance=RequestContext(request))
            elif "delete_confirm" in request.POST: # If confirmation delete button is pressed
                for file in form.cleaned_data["files"]:
                    os.remove(files[file].full_path)
                return HttpResponseRedirect(reverse('accounts-describe'))
            elif "describe" in request.POST: # If describe button is pressed
                # If only one file is choosen, go straight to the last step of the describe process, otherwise go to license selection step
                if len(form.cleaned_data["files"]) > 1 :
                    request.session['describe_sounds'] = [files[x] for x in form.cleaned_data["files"]]
                    return HttpResponseRedirect(reverse('accounts-describe-license'))
                else :
                    request.session['describe_sounds'] = [files[x] for x in form.cleaned_data["files"]]
                    return HttpResponseRedirect(reverse('accounts-describe-sounds'))
            else:
                form = FileChoiceForm(files) # Reset form
                return render_to_response('accounts/describe.html', locals(), context_instance=RequestContext(request))
    else:
        form = FileChoiceForm(files)
    return render_to_response('accounts/describe.html', locals(), context_instance=RequestContext(request))


@login_required
def describe_license(request):
    if request.method == 'POST':
        form = NewLicenseForm(request.POST)
        if form.is_valid():
            request.session['describe_license'] = form.cleaned_data['license']
            return HttpResponseRedirect(reverse('accounts-describe-pack'))
    else:
        form = NewLicenseForm({'license': License.objects.get(name='Attribution')})
    return render_to_response('accounts/describe_license.html', locals(), context_instance=RequestContext(request))

@login_required
def describe_pack(request):
    packs = Pack.objects.filter(user=request.user)
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
    return render_to_response('accounts/describe_pack.html', locals(), context_instance=RequestContext(request))


@login_required
@transaction.autocommit
def describe_sounds(request):
    sounds_to_process = []
    sounds = request.session.get('describe_sounds', False)
    selected_license = request.session.get('describe_license', False)
    selected_pack = request.session.get('describe_pack', False)

    # This is to prevent people browsing to the /home/describe/sounds page
    # without going through the necessary steps.
    # selected_pack can be False, but license and sounds have to be picked at least
    if not (sounds):
        msg = 'Please pick at least one sound.'
        messages.add_message(request, messages.WARNING, msg)
        return HttpResponseRedirect(reverse('accounts-describe'))

    # So SOUNDS_PER_DESCRIBE_ROUND is available in the template
    sounds_per_round = SOUNDS_PER_DESCRIBE_ROUND
    sounds_to_describe = sounds[0:sounds_per_round]
    forms = []
    request.session['describe_sounds_number'] = len(request.session.get('describe_sounds'))

    # If there are no files in the session redirect to the first describe page
    if len(sounds_to_describe) <= 0:
        msg = 'You have finished describing your sounds.'
        messages.add_message(request, messages.WARNING, msg)
        return HttpResponseRedirect(reverse('accounts-describe'))

    if request.method == 'POST':
        # first get all the data
        for i in range(len(sounds_to_describe)):
            prefix = str(i)
            forms.append({})
            forms[i]['sound'] = sounds_to_describe[i]
            forms[i]['description'] = SoundDescriptionForm(request.POST, prefix=prefix)
            forms[i]['geotag'] = GeotaggingForm(request.POST, prefix=prefix)
            forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user),
                                        request.POST,
                                        prefix=prefix)
            forms[i]['license'] = NewLicenseForm(request.POST, prefix=prefix)
        # validate each form
        for i in range(len(sounds_to_describe)):
            for f in ['license', 'geotag', 'pack', 'description']:
                if not forms[i][f].is_valid():
                    return render_to_response('accounts/describe_sounds.html',
                                              locals(),
                                              context_instance=RequestContext(request))
        # all valid, then create sounds and moderation tickets
                
        dirty_packs = []
        for i in range(len(sounds_to_describe)):
            sound = Sound()
            sound.user = request.user
            sound.original_filename = forms[i]['description'].cleaned_data['name']
            sound.original_path = forms[i]['sound'].full_path
            sound.filesize = os.path.getsize(sound.original_path)

            try:
                sound.md5 = md5file(forms[i]['sound'].full_path)
            except IOError:
                messages.add_message(request, messages.ERROR, 'Something went wrong with accessing the file %s.' % sound.original_path)
                continue
            sound.type = get_sound_type(sound.original_path)
            # check if file exists or not
            try:
                existing_sound = Sound.objects.get(md5=sound.md5)
                msg = 'The file %s is already part of freesound and has been discarded, see <a href="%s">here</a>' % \
                    (forms[i]['sound'].name, reverse('sound', args=[existing_sound.user.username, existing_sound.id]))
                messages.add_message(request, messages.WARNING, msg)
                os.remove(forms[i]['sound'].full_path)
                continue
            except Sound.DoesNotExist, e:
                pass

            # set the license
            sound.license = forms[i]['license'].cleaned_data['license']
            sound.save()
            # now move the original
            orig = os.path.splitext(os.path.basename(sound.original_filename))[0]
            sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(orig))
            new_original_path = sound.locations("path")
            if sound.original_path != new_original_path:
                try:
                    os.makedirs(os.path.dirname(new_original_path))
                except OSError:
                    pass
                try:
                    shutil.move(sound.original_path, new_original_path)
                    #shutil.copy(sound.original_path, new_original_path)
                except IOError, e:
                    logger.info("failed to move file from %s to %s" % (sound.original_path, new_original_path), e)
                logger.info("moved original file from %s to %s" % (sound.original_path, new_original_path))
                sound.original_path = new_original_path
                sound.save()

            # set the pack (optional)
            pack = forms[i]['pack'].cleaned_data.get('pack', False)
            new_pack = forms[i]['pack'].cleaned_data.get('new_pack', False)
            if not pack and new_pack:
                pack, created = Pack.objects.get_or_create(user=request.user, name=new_pack)
            if pack:
                sound.pack = pack
                dirty_packs.append(sound.pack)
            # set the geotag (if 'lat' is there, all fields are)
            data = forms[i]['geotag'].cleaned_data
            if not data.get('remove_geotag') and data.get('lat'):
                geotag = GeoTag(user=request.user,
                                lat=data.get('lat'),
                                lon=data.get('lon'),
                                zoom=data.get('zoom'))
                geotag.save()
                sound.geotag = geotag
            # set the tags and descriptions
            data = forms[i]['description'].cleaned_data
            sound.description = data.get('description', '')
            sound.set_tags(data.get('tags'))
            sound.save()
            # remember to process the file
            sounds_to_process.append(sound)
            if request.user.profile.is_whitelisted:
                sound.moderation_state = 'OK'
                sound.save()
                messages.add_message(request, messages.INFO,
                                     'File <a href="%s">%s</a> has been described and has been added to freesound.' % \
                                     (sound.get_absolute_url(), forms[i]['sound'].name))
            else:
                # create moderation ticket!
                ticket = Ticket()
                ticket.title = 'Moderate sound %s' % sound.original_filename
                ticket.source = TICKET_SOURCE_NEW_SOUND
                ticket.status = TICKET_STATUS_NEW
                ticket.queue = Queue.objects.get(name='sound moderation')
                ticket.sender = request.user
                lc = LinkedContent()
                lc.content_object = sound
                lc.save()
                ticket.content = lc
                ticket.save()
                tc = TicketComment()
                tc.sender = request.user
                tc.text = "I've uploaded %s. Please moderate!" % sound.original_filename
                tc.ticket = ticket
                tc.save()
                # add notification that the file was described successfully
                messages.add_message(request, messages.INFO,
                                     'File <a href="%s">%s</a> has been described and is awaiting moderation.' % \
                                     (sound.get_absolute_url(), forms[i]['sound'].name))
            # compute crc
            # TEMPORARY
            try:
                sound.compute_crc()
            except:
                pass
        # remove the files we described from the session and redirect to this page
        request.session['describe_sounds'] = request.session['describe_sounds'][len(sounds_to_describe):]
        # Process the sound
        # N.B. we do this at the end to avoid conflicts between django-web and django-workers
        # If we're not careful django's save() functions will overwrite any processing we
        # do on the workers.
        try:
            for sound in sounds_to_process:
                sound.process()
        except Exception, e:
            audio_logger.error('Sound with id %s could not be scheduled. (%s)' % (sound.id, str(e)))
        for p in dirty_packs:
            p.process()
                            
        if len(request.session['describe_sounds']) <= 0:
            msg = 'You have described all the selected files.'
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
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user),
                                            prefix=prefix,
                                            initial={'pack': selected_pack.id})
            else:
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user),
                                            prefix=prefix)
            if selected_license:
                forms[i]['license'] = NewLicenseForm(initial={'license': selected_license},
                                                     prefix=prefix)
            else:
                forms[i]['license'] = NewLicenseForm(prefix=prefix)
            # cannot include this right now because the remix sources form needs a sound object
            #forms[prefix]['remix'] = RemixForm(prefix=prefix)
        #request.session['describe_sounds'] = request.session['describe_sounds'][5:]
    return render_to_response('accounts/describe_sounds.html', locals(), context_instance=RequestContext(request))


@login_required
def attribution(request):
    qs = Download.objects.filter(user=request.user)
    format = request.GET.get("format", "regular")
    return render_to_response('accounts/attribution.html', combine_dicts(paginate(request, qs, 40), locals()), context_instance=RequestContext(request))


def downloaded_sounds(request, username):
    user=get_object_or_404(User, username__iexact=username)
    qs = Download.objects.filter(user=user.id, sound__isnull=False)
    return render_to_response('accounts/downloaded_sounds.html', combine_dicts(paginate(request, qs, settings.SOUNDS_PER_PAGE), locals()), context_instance=RequestContext(request))

def downloaded_packs(request, username):
    user=get_object_or_404(User, username__iexact=username)
    qs = Download.objects.filter(user=user.id, pack__isnull=False)
    return render_to_response('accounts/downloaded_packs.html', combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE), locals()), context_instance=RequestContext(request))


def latest_content_type(scores):
        if  scores['uploads']>=scores['posts']and scores['uploads']>=scores['comments']:
            return 'sound'
        elif scores['posts']>=scores['uploads'] and scores['posts']>scores['comments']:
            return 'post'
        elif scores['comments']>=scores['uploads'] and scores['comments']>scores['posts']:
            return 'comment'

def create_user_rank(uploaders, posters, commenters):
    upload_weight = 1
    post_weight = 0.7
    comment_weight = 0.0

    user_rank = {}
    for user in uploaders:
        user_rank[user['user']] = {'uploads':user['id__count'], 'posts':0, 'comments':0, 'score':0}
    for user in posters:
        if user['author_id'] in user_rank.keys():
            user_rank[user['author_id']]['posts'] = user['id__count']
        else:
             user_rank[user['author_id']] = {'uploads':0, 'posts':user['id__count'], 'comments':0, 'score':0}
    for user in commenters:
        if user['user_id'] in user_rank.keys():
            user_rank[user['user_id']]['comments'] = user['id__count']
        else:
             user_rank[user['user_id']] = {'uploads':0, 'posts':0, 'comments':user['id__count'], 'score':0}
    sort_list = []
    for user in user_rank.keys():
        user_rank[user]['score'] =  user_rank[user]['uploads'] * upload_weight + \
            user_rank[user]['posts'] * post_weight + user_rank[user]['comments'] * comment_weight
        sort_list.append([user_rank[user]['score'],user])
    return user_rank, sort_list

def accounts(request):
    num_days = 14
    num_active_users = 10
    num_all_time_active_users = 10
    last_time = DBTime.get_last_time() - datetime.timedelta(num_days)

    # select active users last num_days
    latest_uploaders = Sound.public.filter(created__gte=last_time).values("user").annotate(Count('id')).order_by("-id__count")
    latest_posters = Post.objects.filter(created__gte=last_time).values("author_id").annotate(Count('id')).order_by("-id__count")
    latest_commenters = Comment.objects.filter(created__gte=last_time).values("user_id").annotate(Count('id')).order_by("-id__count")
    # rank
    user_rank,sort_list = create_user_rank(latest_uploaders,latest_posters,latest_commenters)

    #retrieve users lists
    most_active_users = User.objects.select_related().filter(id__in=[u[1] for u in sorted(sort_list,reverse=True)[:num_active_users]])
    new_users = User.objects.select_related().filter(date_joined__gte=last_time).filter(id__in=user_rank.keys()).order_by('-date_joined')[:num_active_users+5]
    logged_users = User.objects.select_related().filter(id__in=get_online_users())

    # prepare for view
    most_active_users_display = [[u, latest_content_type(user_rank[u.id]), user_rank[u.id]] for u in most_active_users]
    most_active_users_display=sorted(most_active_users_display, key=lambda usr: user_rank[usr[0].id]['score'],reverse=True)
    new_users_display = [[u, latest_content_type(user_rank[u.id]), user_rank[u.id]] for u in new_users]

    # select all time active users
    all_time_uploaders = Sound.public.values("user").annotate(Count('id')).order_by("-id__count")[:num_all_time_active_users]
    all_time_posters = Post.objects.all().values("author_id").annotate(Count('id')).order_by("-id__count")[:num_all_time_active_users]
    all_time_commenters = Comment.objects.all().values("user_id").annotate(Count('id')).order_by("-id__count")[:num_all_time_active_users]

    # rank
    user_rank,sort_list = create_user_rank(all_time_uploaders,all_time_posters,all_time_commenters)
    #retrieve users list
    all_time_most_active_users = User.objects.select_related().filter(id__in=[u[1] for u in sorted(sort_list,reverse=True)[:num_all_time_active_users]])
    all_time_most_active_users_display = [[u, user_rank[u.id]] for u in all_time_most_active_users]
    all_time_most_active_users_display=sorted(all_time_most_active_users_display, key=lambda usr: user_rank[usr[0].id]['score'],reverse=True)

    return render_to_response('accounts/accounts.html', dict(most_active_users=most_active_users_display, all_time_most_active_users= all_time_most_active_users_display, new_users = new_users_display, logged_users = logged_users, user_rank=user_rank,num_days=num_days), context_instance=RequestContext(request))



def account(request, username):
    try:
        user = User.objects.select_related('profile').get(username__iexact=username)
    except User.DoesNotExist:
        raise Http404
    # expand tags because we will definitely be executing, and otherwise tags is called multiple times
    tags = list(user.profile.get_tagcloud() if user.profile else [])
    latest_sounds = Sound.public.filter(user=user).select_related('license', 'pack', 'geotag', 'user', 'user__profile')[0:settings.SOUNDS_PER_PAGE]
    latest_packs = Pack.objects.select_related().filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:10]
    latest_geotags = Sound.public.select_related('license', 'pack', 'geotag', 'user', 'user__profile').filter(user=user).exclude(geotag=None)[0:10]
    google_api_key = settings.GOOGLE_API_KEY
    home = False
    has_bookmarks = Bookmark.objects.filter(user=user).exists()
    if not user.is_active:
        messages.add_message(request, messages.INFO, 'This account has <b>not been activated</b> yet.')

    return render_to_response('accounts/account.html', locals(), context_instance=RequestContext(request))

logger = logging.getLogger("upload")

def handle_uploaded_file(user_id, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.UPLOADS_PATH, str(user_id))

    logger.info("\thandling file upload")

    try:
        os.mkdir(directory)
    except:
        logger.info("\tfailed creating directory, probably already exist")
        pass

    path = os.path.join(directory, os.path.basename(f.name))
    try:
        logger.info("\topening file: %s", path)
        destination = open(path.encode("utf-8"), 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        logger.info("file upload done")
    except Exception, e:
        logger.warning("failed writing file error: %s", str(e))
        return False

    return True

@csrf_exempt
def upload_file(request):
    """ upload a file. This function does something weird: it gets the session id from the
    POST variables. This is weird but... as far as we know it's not too bad as we only need
    the user login """

    logger.info("start uploading file")

    # get the current session engine
    engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
    session_data = engine.SessionStore(request.POST.get('sessionid', ''))

    try:
        user_id = session_data['_auth_user_id']
        logger.info("\tuser id %s", str(user_id))
    except KeyError:
        logger.warning("failed to get user id from session")
        return HttpResponseBadRequest("You're not logged in. Log in and try again.")

    try:
        request.user = User.objects.get(id=user_id)
        logger.info("\tfound user: %s", request.user.username)
    except User.DoesNotExist:
        logger.warning("user with this id does not exist")
        return HttpResponseBadRequest("user with this ID does not exist.")

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            logger.info("\tform data is valid")
            if handle_uploaded_file(user_id, request.FILES["file"]):
                return HttpResponse("File uploaded OK")
            else:
                return HttpResponseServerError("Error in file upload")
        else:
            logger.warning("form data is invalid: %s", str(form.errors))
            return HttpResponseBadRequest("Form is not valid.")
    else:
        logger.warning("no data in post")
        return HttpResponseBadRequest("No POST data in request")

@login_required
def upload(request, no_flash = False):
    form = UploadFileForm()
    success = False
    error = False
    if no_flash:
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                if handle_uploaded_file(request.user.id, request.FILES["file"]):
                    uploaded_file=request.FILES["file"]
                    success = True
                else:
                    error = True
    return render_to_response('accounts/upload.html', locals(), context_instance=RequestContext(request))


@login_required
def delete(request):
    import time

    encrypted_string = request.GET.get("user", None)

    waited_too_long = False
    
    num_sounds = request.user.sounds.all().count()

    if encrypted_string != None:
        try:
            user_id, now = decrypt(encrypted_string).split("\t")
            user_id = int(user_id)

            if user_id != request.user.id:
                raise PermissionDenied

            link_generated_time = float(now)
            if abs(time.time() - link_generated_time) < 10:
                from forum.models import Post, Thread
                from comments.models import Comment
                from sounds.models import DeletedSound
            
                deleted_user = User.objects.get(id=settings.DELETED_USER_ID)
            
                for post in Post.objects.filter(author=request.user):
                    post.author = deleted_user
                    post.save()
                
                for thread in Thread.objects.filter(author=request.user):
                    thread.author = deleted_user
                    thread.save()
                    
                for comment in Comment.objects.filter(user=request.user):
                    comment.user = deleted_user
                    comment.save()

                for sound in DeletedSound.objects.filter(user=request.user):
                    sound.user = deleted_user
                    sound.save()

                request.user.delete()
                return HttpResponseRedirect(reverse("front-page"))
            else:
                waited_too_long = True
        except:
            pass

    encrypted_link = encrypt(u"%d\t%f" % (request.user.id, time.time()))

    return render_to_response('accounts/delete.html', locals(), context_instance=RequestContext(request))


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


# got characters from rfc3986 (minus @, + which are valid for django usernames)
BAD_USERNAME_CHARACTERS = {':': '_colon_',
                           '/': '_slash_',
                           '?': '_qmark_',
                           '#': '_hash_',
                           '[': '_lbrack1_',
                           ']': '_rbrack1_',
                           '!': '_emark_',
                           '$': '_dollar_',
                           '&': '_amper_',
                           "'": '_quote_',
                           '(': '_lbrack2_',
                           ')': '_rbrack2_',
                           '*': '_stardom_',
                           ',': '_comma_',
                           ';': '_scolon_',
                           '=': '_equal_',
                           '{': '_lbrack3_',
                           '}': '_rbrack3_'
                           }


def transform_username_fs1fs2(fs1_name, fs2_append=''):
    """ Returns a tuple (changed, name) where changed is a boolean
        indicating the name was transformed and name a string
        with the correct username for freesound 2
    """
    if any([x in fs1_name for x in BAD_USERNAME_CHARACTERS.keys()]):
        fs2_name = fs1_name
        for bad_char, replacement in BAD_USERNAME_CHARACTERS.items():
            fs2_name = fs2_name.replace(bad_char, replacement)
        fs2_name = '%s%s' % (fs2_name, fs2_append)

        # If the transformed name is too long, create a hash.
        if len(fs2_name) > 30:
            m = hashlib.md5()
            m.update(fs2_name.encode('utf-8'))
            # Hack: m.hexdigest() is too long.
            fs2_name = base64.urlsafe_b64encode(m.digest())
        return True, fs2_name
    else:
        return False, fs1_name


def login_wrapper(request):
    if request.method == "POST":
        old_name = request.POST.get('username', False)
        if old_name:
            changed, new_name = transform_username_fs1fs2(old_name)
            if changed:
                try:
                    # check if the new name actually exists
                    _ = User.objects.get(username=new_name)
                    msg = """Hi there! Your old username had some weird
    characters in it and we had to change it. It is now <b>%s</b>. If you don't like
    it, please contact us and we'll change it for you.""" % new_name
                    messages.add_message(request, messages.WARNING, msg)
                except User.DoesNotExist:
                    pass
    return authviews.login(request, template_name='accounts/login.html')


@login_required
def email_reset(request):

    if request.method == "POST":
        form = EmailResetForm(request.POST, user = request.user)
        if form.is_valid():

            # save new email info to DB (temporal)
            try:
                rer = ResetEmailRequest.objects.get(user=request.user)
                rer.email = form.cleaned_data['email']
            except ResetEmailRequest.DoesNotExist:
                rer = ResetEmailRequest(user=request.user, email=form.cleaned_data['email'])

            rer.save()


            # send email to the new address
            user = request.user
            email = form.cleaned_data["email"]
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain

            c = {
                'email': email,
                'domain': domain,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': default_token_generator.make_token(user),
                'protocol': 'http',
            }

            subject = loader.render_to_string('accounts/email_reset_subject.txt', c)
            subject = ''.join(subject.splitlines())
            email_body = loader.render_to_string('accounts/email_reset_email.html', c)
            send_mail(subject=subject, email_body=email_body, email_to=[email])

            return HttpResponseRedirect(reverse('accounts.views.email_reset_done'))
    else:
        form = EmailResetForm(user = request.user)

    return render_to_response('accounts/email_reset_form.html',locals(),context_instance=RequestContext(request))


def email_reset_done(request):
    return render_to_response('accounts/email_reset_done.html',locals(),context_instance=RequestContext(request))


@never_cache
def email_reset_complete(request, uidb36=None, token=None):

    # Check that the link is valid and the base36 corresponds to a user id
    assert uidb36 is not None and token is not None # checked by URLconf
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
    except (ValueError, User.DoesNotExist):
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

    # Remove temporal mail change information ftom the DB
    ResetEmailRequest.objects.get(user=user).delete()

    return render_to_response('accounts/email_reset_complete.html',locals(),context_instance=RequestContext(request))

@login_required
def flag_user(request, username = None):

    if request.POST:
        flagged_user = User.objects.get(username__iexact=request.POST["username"])
        reporting_user = request.user
        object_id = request.POST["object_id"]

        if object_id:
            if request.POST["flag_type"] == "PM":
                flagged_object = Message.objects.get(id = object_id)
            elif request.POST["flag_type"] == "FP":
                flagged_object = Post.objects.get(id = object_id)
            elif request.POST["flag_type"] == "SC":
                flagged_object = Comment.objects.get(id = object_id)
            else:
                return HttpResponse(json.dumps({"errors":True}), mimetype='application/javascript')
        else:
            return HttpResponse(json.dumps({"errors":True}), mimetype='application/javascript')

        uflag = UserFlag(user = flagged_user, reporting_user = reporting_user, content_object = flagged_object)
        uflag.save()

        reports_count = UserFlag.objects.filter(user__username = flagged_user.username).values('reporting_user').distinct().count()
        if  reports_count == settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION or reports_count == settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING:
            # Get all flagged objects by the user, create links to admin pages and send email
            flagged_objects = UserFlag.objects.filter(user__username = flagged_user.username)
            urls = []
            added_objects = []
            for object in flagged_objects:
                key = str(object.content_type) + str(object.object_id)
                if not key in added_objects:
                    added_objects.append(key)
                    try:
                        obj = object.content_type.get_object_for_this_type(id=object.object_id)
                        url = reverse('admin:%s_%s_change' %(obj._meta.app_label,  obj._meta.module_name),  args=[obj.id] )
                        urls.append([str(object.content_type),request.build_absolute_uri(url)])
                    except Exception:
                        urls.append([str(object.content_type),"url not available"])

            user_url = reverse('admin:%s_%s_delete' %(flagged_user._meta.app_label,  flagged_user._meta.module_name),  args=[flagged_user.id] )
            user_url = request.build_absolute_uri(user_url)
            clear_url = reverse("clear-flags-user", args=[flagged_user.username])
            clear_url = request.build_absolute_uri(clear_url)

            if reports_count < settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING:
                template_to_use = 'accounts/report_spammer_admins.txt'
            else:
                template_to_use = 'accounts/report_blocked_spammer_admins.txt'

            to_emails = []
            for mail in settings.ADMINS:
                to_emails.append(mail[1])
            send_mail_template(u'Spam report for user ' + flagged_user.username , template_to_use, locals(), None, to_emails)

        return HttpResponse(json.dumps({"errors":None}), mimetype='application/javascript')
    else:
        return HttpResponse(json.dumps({"errors":True}), mimetype='application/javascript')

@login_required
def clear_flags_user(request, username):
    if request.user.is_superuser or request.user.is_staff:
        flags = UserFlag.objects.filter(user__username = username)
        num = len(flags)
        for flag in flags:
            flag.delete()

        return render_to_response('accounts/flags_cleared.html',locals(),context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('accounts-login'))

def donate_redirect(request):
    pledgie_campaign_url = "http://pledgie.com/campaigns/%d/" % settings.PLEDGIE_CAMPAIGN
    return HttpResponseRedirect(pledgie_campaign_url)