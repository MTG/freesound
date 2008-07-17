from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forms import UploadFileForm
from uploadhandler import ProgressUploadHandler
import hashlib
import os
import random

@login_required
def home(request):
    pass

@login_required
def edit(request):
    pass

@login_required
def describe(request):
    pass

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
    directory_ok = os.path.join(settings.FILES_UPLOAD_DIRECTORY, str(request.user.id))
    
    try:
        os.mkdir(directory)
        os.mkdir(directory_ok)
    except:
        pass

    destination = open(os.path.join(directory, f.name), 'wb')
    for chunk in f.chunks():
        destination.write(chunk)
        
    file(os.path.join(directory_ok, f.name), "w").write("")


@login_required
def upload(request, unique_id=None):
    
    if unique_id == None:
        unique_id = "".join(random.sample("0123456789", 10))

    request.upload_handlers.insert(0, ProgressUploadHandler(unique_id))
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            handle_uploaded_file(request, request.FILES["file"])
            
            return HttpResponseRedirect(reverse("accounts-describe"))
    else:
        
        form = UploadFileForm(initial={'unique_id' : unique_id})
    
    return render_to_response('accounts/upload.html', { "unique_id": unique_id, "upload_form" : form }, context_instance=RequestContext(request))


@login_required
def upload_progress(request, unique_id):
    progress = cache.get(unique_id)
    
    # TODO: encode to JSON before sending + set JSON headers!!

    if progress:
        return HttpResponse(progress)
    else:
        return HttpProgress("0")