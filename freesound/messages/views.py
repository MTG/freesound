from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from models import *

from django.views.generic.list_detail import object_list

def combine_dicts(dict1, dict2):
    return dict(dict1.items() + dict2.items())

def get_messages(request, qs, **kwargs):
    paginator = Paginator(qs, 20)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('messages/message_list.html', combine_dicts(locals(), kwargs), context_instance=RequestContext(request))

# base query object
base_qs = Message.objects.select_related('body', 'user_from', 'user_to')

@login_required
def inbox(request):
    qs = base_qs.filter(user_to=request.user, is_archived=False, is_sent=False)
    return get_messages(request, qs, page_title="Inbox")

@login_required
def sent_messages(request):
    qs = base_qs.filter(user_from=request.user, is_archived=False, is_sent=True)
    return get_messages(request, qs, page_title="Sent messages")

@login_required
def archived_messages(request):
    qs = base_qs.filter(user_to=request.user, is_archived=True, is_sent=False)
    return get_messages(request, qs, page_title="Archived messages")

@login_required
def message(request, message_id):
    try:
        message = base_qs.get(id=message_id)
    except Message.DoesNotExist:
        raise Http404
    
    if message.user_from != request.user and message.user_to != request.user:
        raise Http404
    
    return render_to_response('messages/message.html', locals(), context_instance=RequestContext(request))