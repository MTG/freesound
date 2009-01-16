from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from models import *

@login_required
def messages(request):
    paginator = Paginator(Message.objects.filter(user_to=request.user, is_archived=False, is_sent=False), 20)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('messages/index.html', locals(), context_instance=RequestContext(request))

@login_required
def archive(request):
    message_type = "Archived"
    paginator = Paginator(Message.objects.filter(user_to=request.user, is_archived=False, is_sent=False), 20)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('messages/index.html', locals(), context_instance=RequestContext(request))

@login_required
def message(request, message_id):
    return render_to_response('', locals(), context_instance=RequestContext(request))

@login_required
def sent(request):
    return render_to_response('', locals(), context_instance=RequestContext(request))