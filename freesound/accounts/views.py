from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forms import UploadFileForm, FileChoiceForm, RegistrationForm
from sounds.models import Sound, Pack
from utils.encryption import decrypt, encrypt
from utils.filesystem import generate_tree
from utils.mail import send_mail_template
import os

def activate_user(request, activation_key):
    try:
        user = User.objects.get(id=int(decrypt(activation_key)))
        user.is_active = True
        user.save()
        return HttpResponseRedirect(reverse("accounts-home"))
    except User.DoesNotExist: #@UndefinedVariable
        return render_to_response('accounts/activate.html', { 'user_does_not_exist': True }, context_instance=RequestContext(request))
    except:
        return render_to_response('accounts/activate.html', { 'decode_error': True }, context_instance=RequestContext(request))


def registration(request):
    if request.method == "POST":
        form = RegistrationForm(request, request.POST)
        if form.is_valid():
            user = form.save()
            
            encrypted_user_id = encrypt(str(user.id))
            
            send_mail_template(u'activation link.', 'accounts/email_activation.txt', locals(), None, user.email)
            
            return render_to_response('accounts/registration_done.html', locals(), context_instance=RequestContext(request))
    else:
        form = RegistrationForm(request)
        
    return render_to_response('accounts/registration.html', locals(), context_instance=RequestContext(request))


@login_required
def home(request):
    pass


@login_required
def edit(request):
    pass


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
    pass


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
    return render_to_response('accounts/account.html', locals(), context_instance=RequestContext(request)) 


def handle_uploaded_file(request, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.FILES_UPLOAD_DIRECTORY, str(request.user.id))
    
    try:
        os.mkdir(directory)
    except:
        pass

    destination = open(os.path.join(directory, f.name), 'wb')
    for chunk in f.chunks():
        destination.write(chunk)


def upload_file(request):
    """ upload a file. This function does something weird: it gets the session id from the
    POST variables. This is weird but... as far as we know it's not too bad as we only need
    the user login """
    
    # get the current session engine
    engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
    session_data = engine.SessionStore(request.POST.get('sessionid', ''))
    
    try:
        user_id = session_data['_auth_user_id']
    except KeyError:
        return HttpResponseBadRequest("User is not logged in.")
    
    try:
        request.user = User.objects.get(id=user_id)
    except User.DoesNotExist: #@UndefinedVariable
        return HttpResponseBadRequest("User with this ID does not exist.")

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            handle_uploaded_file(request, request.FILES["file"])
            return HttpResponse("File uploaded OK")
        else:
            return HttpResponseBadRequest("Form is not valid.")
    else:
        return HttpResponseBadRequest("No POST data in request")

@login_required
def upload(request):
    return render_to_response('accounts/upload.html', locals(), context_instance=RequestContext(request))