from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forms import UploadFileForm, FileChoiceForm, RegistrationForm
from utils.encryption import decrypt, encrypt
from utils.filesystem import generate_tree
from utils.mail import send_mail_template
import os
import random

def activate_user(request, activation_key):
    try:
        user = User.objects.get(id=int(decrypt(activation_key)))
        user.is_active = True
        user.save()
        return HttpResponseRedirect(reverse("accounts-home"))
    except User.DoesNotExist:
        return render_to_response('accounts/activate.html', { 'user_does_not_exist': True }, context_instance=RequestContext(request))
    except:
        return render_to_response('accounts/activate.html', { 'decode_error': True }, context_instance=RequestContext(request))


def registration(request):
    if request.method == "POST":
        form = RegistrationForm(request, request.POST)
        if form.is_valid():
            user = form.save()
            
            encrypted_user_id = encrypt(str(user.id))
            current_site = Site.objects.get_current()
            
            send_mail_template(u'Activation link.', 'accounts/email_activation.txt', locals(), None, user.email)
            
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

    return render_to_response('accounts/describe.html', { "file_structure": file_structure, "form": form }, context_instance=RequestContext(request))


@login_required
def attribution(request):
    pass


def accounts(request):
    pass


def account(request, username):
    pass


def handle_uploaded_file(request, f):
    # handle a file uploaded to the app. Basically act as if this file was uploaded through FTP
    directory = os.path.join(settings.FILES_UPLOAD_DIRECTORY, str(request.user.id))
    directory_ok = os.path.join(settings.FILES_UPLOAD_OK_DIRECTORY, str(request.user.id))
    
    try:
        os.mkdir(directory)
        os.mkdir(directory_ok)
    except:
        pass

    destination = open(os.path.join(directory, f.name), 'wb')
    for chunk in f.chunks():
        destination.write(chunk)
        
    file(os.path.join(directory_ok, f.name), "w").write(" ")


@login_required
def upload(request):
        
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            handle_uploaded_file(request, request.FILES["file"])
            return HttpResponseRedirect(reverse("accounts-describe"))
    else:
        form = UploadFileForm()
    
    return render_to_response('accounts/upload.html', { "upload_form" : form }, context_instance=RequestContext(request))


@login_required
def upload_progress(request, unique_id):
    return render_to_response('accounts/upload-progress.html', { "progress": cache.get(unique_id) }, context_instance=RequestContext(request))