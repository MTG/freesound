import datetime, logging, os, tempfile, uuid, shutil
from accounts.forms import UploadFileForm, FileChoiceForm, RegistrationForm, \
    ReactivationForm, UsernameReminderForm, ProfileForm, AvatarForm
from accounts.models import Profile
from comments.models import Comment
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseBadRequest, HttpResponseNotFound, Http404, \
    HttpResponsePermanentRedirect, HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from forum.models import Post
from operator import itemgetter
from sounds.models import Sound, Pack, Download, License
from sounds.forms import NewLicenseForm, PackForm, SoundDescriptionForm, GeotaggingForm, RemixForm
from utils.dbtime import DBTime
from utils.onlineusers import get_online_users
from utils.encryption import decrypt, encrypt
from utils.filesystem import generate_tree, md5file
from utils.functional import combine_dicts
from utils.images import extract_square
from utils.mail import send_mail_template
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
import hashlib, base64
from tickets.views import new_sound_tickets_qs, new_support_tickets_qs

audio_logger = logging.getLogger('audio')

@login_required
def bulk_license_change(request):
    if request.method == 'POST':
        form = NewLicenseForm(request.POST)
        if form.is_valid():
            license = form.cleaned_data['license']
            Sound.objects.filter(user=request.user).update(license=license)
            # update old license flag
            Profile.objects.filter(user=request.user).update(has_old_license=False)
            # update cache
            cache.set("has-old-license-%s" % request.user.id, False, 2592000)
            return HttpResponseRedirect(reverse('accounts-home'))
    else:
        form = NewLicenseForm()
    return render_to_response('accounts/choose_new_license.html', locals(), context_instance=RequestContext(request))


def activate_user(request, activation_key):
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
    except TypeError:
        return render_to_response('accounts/activate.html', { 'decode_error': True }, context_instance=RequestContext(request))

def send_activation(user):
    encrypted_user_id = encrypt(str(user.id))
    send_mail_template(u'activation link.', 'accounts/email_activation.txt', locals(), None, user.email)

def registration(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse("accounts-home"))

    if request.method == "POST":
        form = RegistrationForm(request, request.POST)
        if form.is_valid():
            user = form.save()
            send_activation(user)
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
            send_activation(user)
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
    tags = user.profile.get_tagcloud()
    latest_sounds = Sound.public.select_related().filter(user=user)[0:5]
    latest_packs = Pack.objects.select_related().filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:5]
    latest_geotags = Sound.public.filter(user=user).exclude(geotag=None)[0:10]
    google_api_key = settings.GOOGLE_API_KEY
    home = True
    if home:
        new_sounds_qs = new_sound_tickets_qs()
        new_support_qs = new_support_tickets_qs()
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
        profile_form = ProfileForm(request.POST, instance=profile, prefix="profile")
        if profile_form.is_valid():
            profile_form.save()
            return HttpResponseRedirect(reverse("accounts-home"))
    else:
        profile_form = ProfileForm(instance=profile, prefix="profile")

    if is_selected("image"):
        image_form = AvatarForm(request.POST, request.FILES, prefix="image")
        if image_form.is_valid():
            if image_form.cleaned_data["remove"]:
                profile.has_avatar = False
                profile.save()
            else:
                if request.FILES["image-file"]:
                    handle_uploaded_image(profile, request.FILES["image-file"])
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
            request.session['describe_sounds'] = [files[x] for x in form.cleaned_data["files"]]
            return HttpResponseRedirect(reverse('accounts-describe-license'))
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
def describe_sounds(request):
    sounds_to_process = []
    sounds = request.session.get('describe_sounds', False)
    selected_license = request.session.get('describe_license', False)
    selected_pack = request.session.get('describe_pack', False)

    # This is to prevent people browsing to the /home/describe/sounds page
    # without going through the necessary steps.
    # selected_pack can be False, but license and sounds have to be picked at least
    if not (sounds and selected_license):
        msg = 'Please pick at least some sounds and a license.'
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
            for f in ['description', 'geotag', 'pack', 'license']:
                if not forms[i][f].is_valid():
                    # if not valid return to the same form!
                    return render_to_response('accounts/describe_sounds.html',
                                              locals(),
                                              context_instance=RequestContext(request))
        # all valid, then create sounds and moderation tickets
        for i in range(len(sounds_to_describe)):
            sound = Sound()
            sound.user = request.user
            sound.original_filename = forms[i]['sound'].name
            sound.original_path = forms[i]['sound'].full_path
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
                sound.pack.is_dirty = True
                sound.pack.save()
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
            forms[i]['description'] = SoundDescriptionForm(prefix=prefix)
            forms[i]['geotag'] = GeotaggingForm(prefix=prefix)
            if selected_pack:
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user),
                                            prefix=prefix,
                                            initial={'pack': selected_pack.id})
            else:
                forms[i]['pack'] = PackForm(Pack.objects.filter(user=request.user),
                                            prefix=prefix)
            if selected_license:
                forms[i]['license'] = NewLicenseForm({'license': selected_license},
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
    latest_uploaders = Sound.objects.filter(created__gte=last_time).values("user").annotate(Count('id')).order_by("-id__count")
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
    all_time_uploaders = Sound.objects.all().values("user").annotate(Count('id')).order_by("-id__count")[:num_all_time_active_users]
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
    tags = user.profile.get_tagcloud()
    latest_sounds = Sound.objects.select_related('license', 'pack', 'geotag', 'user', 'user__profile').filter(user=user)[0:settings.SOUNDS_PER_PAGE]
    latest_packs = Pack.objects.select_related().filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:10]
    latest_geotags = Sound.public.select_related('license', 'pack', 'geotag', 'user', 'user__profile').filter(user=user).exclude(geotag=None)[0:10]
    google_api_key = settings.GOOGLE_API_KEY
    home = False
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
def upload(request):
    return render_to_response('accounts/upload.html', locals(), context_instance=RequestContext(request))


@login_required
def delete(request):
    import time

    encrypted_string = request.GET.get("user", None)

    waited_too_long = False

    if encrypted_string != None:
        try:
            user_id, now = decrypt(encrypted_string).split("\t")
            user_id = int(user_id)

            if user_id != request.user.id:
                raise PermissionDenied

            link_generated_time = float(now)
            if abs(time.time() - link_generated_time) < 10:
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
            try:
                m = hashlib.md5()
                m.update(fs2_name.encode('utf-8'))
            except UnicodeEncodeError:
                print 10*'#', fs1_name, fs2_name
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



