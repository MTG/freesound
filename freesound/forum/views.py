from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from models import *

def forums(request):
    forums = Forum.objects.all().select_related()
    return render_to_response('forum/index.html', locals(), context_instance=RequestContext(request))

def forum(request, forum_name_slug):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    threads = Thread.objects.filter(forum=forum).select_related()[0:10]
    return render_to_response('forum/threads.html', locals(), context_instance=RequestContext(request))

def thread(request, forum_name_slug, thread_id):
    pass

def add_post(request, thread_id=None):
    pass

def edit_post(request, post_id):
    pass