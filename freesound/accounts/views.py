from accounts.forms import UploadFileForm, FileChoiceForm, RegistrationForm, \
    ReactivationForm, UsernameReminderForm, ProfileForm
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
from utils.mail import send_mail_template
from utils.pagination import paginate
import os
import logging

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

@login_required
def edit(request):
    profile = request.user.profile
    
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("accounts-home"))
    else:
        form = ProfileForm(instance=profile)
        
    return render_to_response('accounts/edit.html', dict(form=form, sent=False), context_instance=RequestContext(request))


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
    pass

def account(request, username):
    user = get_object_or_404(User, username__iexact=username)
    # expand tags because we will definitely be executing, and otherwise tags is called multiple times
    tags = user.profile.get_tagcloud()
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
        logger.info("failed creating directory, might already exist")
        pass

    path = os.path.join(directory, f.name)
    try:
        logger.info("\topening file: %s", path)
        destination = open(path, 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        logger.info("file upload done")
    except IOError, e:
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