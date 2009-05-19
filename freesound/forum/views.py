from django.conf import settings, settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from models import *
from forms import *

def forums(request):
    forums = Forum.objects.select_related('last_post', 'last_post__author', 'last_post__thread').all()
    return render_to_response('forum/index.html', locals(), context_instance=RequestContext(request))


def forum(request, forum_name_slug):
    try:
        forum = Forum.objects.get(name_slug=forum_name_slug)
    except Forum.DoesNotExist:
        raise Http404
    
    paginator = Paginator(Thread.objects.filter(forum=forum).select_related('last_post', 'last_post__author'), settings.FORUM_THREADS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('forum/threads.html', locals(), context_instance=RequestContext(request))


def thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id)

    paginator = Paginator(Post.objects.select_related('author', 'author__profile').filter(thread=thread), settings.FORUM_POSTS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('forum/thread.html', locals(), context_instance=RequestContext(request))


def post(request, forum_name_slug, thread_id, post_id):
    post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug)

    posts_before = Post.objects.filter(thread=post.thread, created__lt=post.created).count()
    page = 1 + posts_before / settings.FORUM_POSTS_PER_PAGE
    url = post.thread.get_absolute_url() + "?page=%d#post%d" % (page, post.id)

    return HttpResponseRedirect(url)


@login_required
def reply(request, forum_name_slug, thread_id, post_id=None):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, id=thread_id, forum=forum)
    
    if post_id:
        post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug)
        quote = loader.render_to_string('forum/quote_style.html', {'post':post})
    else:
        post = None
        quote = ""
    
    if request.method == 'POST':
        form = PostReplyForm(quote, request.POST)
        if form.is_valid():
            post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread)
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        if quote:
            form = PostReplyForm(quote, {'body':quote})
        else:
            form = PostReplyForm(quote)
        
    return render_to_response('forum/reply.html', locals(), context_instance=RequestContext(request))


@login_required
def new_thread(request, forum_name_slug):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)

    if request.method == 'POST':
        form = NewThreadForm(request.POST)
        if form.is_valid():
            thread = Thread.objects.create(forum=forum, author=request.user, title=form.cleaned_data["title"])
            post = Post.objects.create(author=request.user, body=form.cleaned_data['body'], thread=thread)
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = NewThreadForm()
        
    return render_to_response('forum/new_thread.html', locals(), context_instance=RequestContext(request))