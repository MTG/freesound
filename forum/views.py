from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, \
    HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from forum.forms import PostReplyForm, NewThreadForm
from forum.models import Forum, Thread, Post, Subscription
from utils.functional import combine_dicts
from utils.mail import send_mail_template
from utils.pagination import paginate
from utils.search.search_forum import add_post_to_solr
import logging
import re

logger = logging.getLogger("web")

def deactivate_spammer(user_id):
    from django.contrib.auth.models import User
    from django.contrib.sessions.models import Session
    user = User.objects.get(id=user_id)
    Post.objects.filter(author=user).delete()
    Thread.objects.filter(author=user).delete()
    [s.delete() for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == user.id]
    user.is_active = False
    user.save()


def forums(request):
    forums = Forum.objects.select_related('last_post', 'last_post__author', 'last_post__thread').all()
    return render_to_response('forum/index.html', locals(), context_instance=RequestContext(request))


def forum(request, forum_name_slug):
    try:
        forum = Forum.objects.get(name_slug=forum_name_slug)
    except Forum.DoesNotExist: #@UndefinedVariable
        raise Http404

    paginator = paginate(request, Thread.objects.filter(forum=forum).select_related('last_post', 'last_post__author'), settings.FORUM_THREADS_PER_PAGE)

    return render_to_response('forum/threads.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))


def thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id)

    paginator = paginate(request, Post.objects.select_related('author', 'author__profile').filter(thread=thread), settings.FORUM_POSTS_PER_PAGE)

    # a logged in user watching a thread can activate his subscription to that thread!
    # we assume the user has seen the latest post if he is browsing the thread
    # this is not entirely correct, but should be close enough
    if request.user.is_authenticated():
        Subscription.objects.filter(thread=thread, subscriber=request.user, is_active=False).update(is_active=True)

    return render_to_response('forum/thread.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))


def latest_posts(request):
    paginator = paginate(request, Post.objects.select_related('author', 'author__profile', 'thread', 'thread__forum').order_by('-created').all(), settings.FORUM_POSTS_PER_PAGE)
    hide_search = True
    return render_to_response('forum/latest_posts.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))


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
        form = PostReplyForm(request, quote, request.POST)
        if form.is_valid():
            post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread)
            add_post_to_solr(post)
            if form.cleaned_data["subscribe"]:
                subscription, created = Subscription.objects.get_or_create(thread=thread, subscriber=request.user)
                if not subscription.is_active:
                    subscription.is_active = True
                    subscription.save()

            # figure out if there are active subscriptions in this thread
            emails_to_notify = []
            for subscription in Subscription.objects.filter(thread=thread, is_active=True).exclude(subscriber=request.user):
                emails_to_notify.append(subscription.subscriber.email)
                logger.info("NOTIFY %s" % subscription.subscriber.email)
                subscription.is_active = False
                subscription.save()

            if emails_to_notify:
                send_mail_template(u"topic reply notification - " + thread.title, "forum/email_new_post_notification.txt", dict(post=post, thread=thread, forum=forum), email_from=None, email_to=emails_to_notify)

            return HttpResponseRedirect(post.get_absolute_url())
    else:
        if quote:
            form = PostReplyForm(request, quote, {'body':quote})
        else:
            form = PostReplyForm(request, quote)

    return render_to_response('forum/reply.html', locals(), context_instance=RequestContext(request))


@login_required
def new_thread(request, forum_name_slug):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)

    if request.method == 'POST':
        form = NewThreadForm(request.POST)
        if form.is_valid():
            thread = Thread.objects.create(forum=forum, author=request.user, title=form.cleaned_data["title"])
            post = Post.objects.create(author=request.user, body=form.cleaned_data['body'], thread=thread)
            add_post_to_solr(post)

            if form.cleaned_data["subscribe"]:
                Subscription.objects.create(subscriber=request.user, thread=thread, is_active=True)

            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = NewThreadForm()

    return render_to_response('forum/new_thread.html', locals(), context_instance=RequestContext(request))


@login_required
def unsubscribe_from_thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id)
    Subscription.objects.filter(thread=thread, subscriber=request.user).delete()
    return render_to_response('forum/unsubscribe_from_thread.html', locals(), context_instance=RequestContext(request))


def old_topic_link_redirect(request):
    post_id = request.GET.get("p", False)
    if post_id:
        post_id = re.sub("\D", "", post_id)
        try:
            post = get_object_or_404(Post, id=post_id)
        except ValueError:
            raise Http404
        return HttpResponsePermanentRedirect(reverse('forums-post', args=[post.thread.forum.name_slug, post.thread.id, post.id]))

    thread_id = request.GET.get("t", False)
    if thread_id:
        thread_id = re.sub("\D", "", thread_id)
        try:
            thread = get_object_or_404(Thread, id=thread_id)
        except ValueError:
            raise Http404
        return HttpResponsePermanentRedirect(reverse('forums-thread', args=[thread.forum.name_slug, thread.id]))

    raise Http404

@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user or request.user.has_perm('forum.delete_post'):
        return render_to_response('forum/confirm_deletion.html',
                                  locals(),
                                  context_instance=RequestContext(request))
    else:
        raise Http404


@login_required
def post_delete_confirm(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user or request.user.has_perm('forum.delete_post'):
        thread = post.thread
        post.delete()
        try:
            return HttpResponseRedirect(reverse('forums-post', args=[thread.forum.name_slug, thread.id, thread.last_post.id]))
        except (Post.DoesNotExist, Thread.DoesNotExist, AttributeError), e:
            return HttpResponseRedirect(reverse('forums-forums'))
    else:
        raise Http404

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user or request.user.has_perm('forum.change_post'):
        if request.method == 'POST':
            form = PostReplyForm(request, '', request.POST)
            if form.is_valid():
                post.body = form.cleaned_data['body']
                post.save()
                return HttpResponseRedirect(reverse('forums-post', args=[post.thread.forum.name_slug, post.thread.id, post.id]))
        else:
            form = PostReplyForm(request, '', {'body': post.body})
        return render_to_response('forum/post_edit.html',
                                  locals(),
                                  context_instance=RequestContext(request))
    else:
        raise Http404