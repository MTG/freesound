from accounts.forms import UploadFileForm, FileChoiceForm, RegistrationForm, \
    ReactivationForm, UsernameReminderForm, ProfileForm, AvatarForm
from accounts.models import Profile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from sounds.models import Sound, Pack, Download
from utils.encryption import decrypt, encrypt
from utils.filesystem import generate_tree
from utils.functional import combine_dicts
from utils.images import extract_square
from utils.mail import send_mail_template
from utils.pagination import paginate
from utils.dbtime import DBTime
import logging
import os
import tempfile
import datetime
from forum.models import Post
from comments.models import Comment
from operator import itemgetter


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
    latest_sounds = Sound.public.filter(user=user)[0:5]
    latest_packs = Pack.objects.filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:5]
    latest_geotags = Sound.public.filter(user=user).exclude(geotag=None)[0:10]
    google_api_key = settings.GOOGLE_API_KEY
    home = True
    return render_to_response('accounts/account.html', locals(), context_instance=RequestContext(request))


def handle_uploaded_image(profile, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.PROFILE_IMAGES_PATH, str(profile.user.id/1000))
    
    logger.info("\thandling profile image upload")
    
    try:
        os.mkdir(directory)
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

    path_s = os.path.join(directory, str(profile.user.id) + "_s.jpg")
    path_m = os.path.join(directory, str(profile.user.id) + "_m.jpg")
    path_l = os.path.join(directory, str(profile.user.id) + "_l.jpg")
    
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
    
    file_structure, files = generate_tree(os.path.join(settings.FILES_UPLOAD_DIRECTORY, str(request.user.id)))
    file_structure.name = "Your uploaded files"
    
    if request.method == 'POST':
        form = FileChoiceForm(files.items(), request.POST)
        
        if form.is_valid():
            return HttpResponse(str(form.cleaned_data["files"]))
        else:
            return HttpResponseRedirect(reverse("accounts-describe"))
    else:
        form = FileChoiceForm(files.items())

    return render_to_response('accounts/describe.html', locals(), context_instance=RequestContext(request))


@login_required
def attribution(request):
    qs = Download.objects.filter(user=request.user)
    format = request.GET.get("format", "regular")
    return render_to_response('accounts/attribution.html', combine_dicts(paginate(request, qs, 40), locals()), context_instance=RequestContext(request))

def accounts(request):
    num_days = 7
    num_active_users = 50
    last_time = DBTime.get_last_time() - datetime.timedelta(num_days)
    active_users = {}
    user_cloud = []
    upload_weight = 1
    post_weight = 1
    comment_weight = 1

    latest_uploaders =  Sound.objects.filter(created__gte=last_time).values("user").annotate(Count('id')).order_by()
    latest_posters = Post.objects.filter(created__gte=last_time).values("author_id").annotate(Count('id')).order_by()
    latest_commenters = Comment.objects.filter(created__gte=last_time).values("user_id").annotate(Count('id')).order_by()
    
    for user in latest_uploaders:
	active_users[user['user']] = {'uploads':user['id__count'],'posts':0,'comments':0}

    for user in latest_posters:
	if user['author_id'] in active_users.keys():
	    active_users[user['author_id']]['posts'] = user['id__count']
	else:
	    active_users[user['author_id']] = {'uploads':0,'posts':user['id__count'],'comments':0}

    for user in latest_commenters:
	if user['user_id'] in active_users.keys():
	    active_users[user['user_id']]['comments'] = user['id__count']
	else:
	    active_users[user['user_id']] = {'uploads':0,'posts':0,'comments':user['id__count']}
	

    for user,scores in active_users.items()[:num_active_users]:
	user_name = User.objects.get(pk=user).username
	user_cloud.append({\
	    'name':user_name,\
	    'count':scores['uploads'] * upload_weight + scores['posts'] * post_weight + scores['comments'] * comment_weight})

    return render_to_response('accounts/accounts.html', dict(most_active_users=user_cloud,num_days = num_days), context_instance=RequestContext(request))


def account(request, username):
    user = get_object_or_404(User, username__iexact=username)
    # expand tags because we will definitely be executing, and otherwise tags is called multiple times
    tags = user.profile.get_tagcloud()
    print tags
    for t in tags:
	print t, type(t)
    latest_sounds = Sound.public.filter(user=user)[0:settings.SOUNDS_PER_PAGE]
    latest_packs = Pack.objects.filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:10]
    latest_geotags = Sound.public.filter(user=user).exclude(geotag=None)[0:10]
    google_api_key = settings.GOOGLE_API_KEY
    home = False
    return render_to_response('accounts/account.html', locals(), context_instance=RequestContext(request)) 

logger = logging.getLogger("upload")

def handle_uploaded_file(user_id, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.FILES_UPLOAD_DIRECTORY, str(user_id))
    
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
        return HttpResponseBadRequest("user is not logged in a.k.a. failed session id")
    
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
            handle_uploaded_file(user_id, request.FILES["file"])
            return HttpResponse("File uploaded OK")
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
