"""
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.newforms import ModelForm
from django.template.loader import render_to_string
from django.utils.http import urlquote
from registration.forms import *
from registration.models import *
from registration.utilities import send_admin_mail, send_email_with_attachement
import os, tempfile
"""

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from sounds.models import Sound

def front_page(request):
    return render_to_response('sounds/home_page.html', {}, context_instance=RequestContext(request))
 