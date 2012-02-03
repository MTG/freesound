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
import datetime
from django.contrib import messages

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


class last_action(object):
    def __init__(self, view_func):
        self.view_func = view_func
        self.__name__ = view_func.__name__
        self.__doc__ = view_func.__doc__
    
    def __call__(self, request, *args, **kwargs):
        
        if not request.user.is_authenticated():
            return self.view_func(request, *args, **kwargs)

        from datetime import datetime, timedelta
        date_format = "%Y-%m-%d %H:%M:%S:%f"
        date2string = lambda date: date.strftime(date_format)
        string2date = lambda date_string: datetime.strptime(date_string, date_format)
        
        key = "forum-last-visited"
        
        now = datetime.now()
        now_as_string = date2string(now)
        
        if key not in request.COOKIES or not request.session.get(key, False):
            request.session[key] = now_as_string
        elif now - string2date(request.COOKIES[key]) > timedelta(minutes=30):
            request.session[key] = request.COOKIES[key]
        
        request.last_action_time = string2date(request.session.get(key, now_as_string))
        
        reply_object = self.view_func(request, *args, **kwargs)
        
        reply_object.set_cookie(key, now_as_string, 60*60*24*30) # 30 days
        
        return reply_object
            

@last_action
def forums(request):
    forums = Forum.objects.select_related('last_post', 'last_post__author', 'last_post__thread').all()
    return render_to_response('forum/index.html', locals(), context_instance=RequestContext(request))


@last_action
def forum(request, forum_name_slug):
    try:
        forum = Forum.objects.get(name_slug=forum_name_slug)
    except Forum.DoesNotExist: #@UndefinedVariable
        raise Http404

    paginator = paginate(request, Thread.objects.filter(forum=forum, first_post__moderation_state="OK").select_related('last_post', 'last_post__author'), settings.FORUM_THREADS_PER_PAGE)

    return render_to_response('forum/threads.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))


@last_action
def thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id, first_post__moderation_state="OK")

    paginator = paginate(request, Post.objects.select_related('author', 'author__profile').filter(thread=thread, moderation_state="OK"), settings.FORUM_POSTS_PER_PAGE)

    # a logged in user watching a thread can activate his subscription to that thread!
    # we assume the user has seen the latest post if he is browsing the thread
    # this is not entirely correct, but should be close enough
    if request.user.is_authenticated():
        Subscription.objects.filter(thread=thread, subscriber=request.user, is_active=False).update(is_active=True)

    return render_to_response('forum/thread.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))

@last_action
def latest_posts(request):
    paginator = paginate(request, Post.objects.select_related('author', 'author__profile', 'thread', 'thread__forum').filter(moderation_state="OK").order_by('-created').all(), settings.FORUM_POSTS_PER_PAGE)
    hide_search = True
    return render_to_response('forum/latest_posts.html', combine_dicts(locals(), paginator), context_instance=RequestContext(request))


@last_action
def post(request, forum_name_slug, thread_id, post_id):
    post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug, moderation_state="OK")

    posts_before = Post.objects.filter(thread=post.thread, moderation_state="OK", created__lt=post.created).count()
    page = 1 + posts_before / settings.FORUM_POSTS_PER_PAGE
    url = post.thread.get_absolute_url() + "?page=%d#post%d" % (page, post.id)

    return HttpResponseRedirect(url)


@login_required
def reply(request, forum_name_slug, thread_id, post_id=None):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, id=thread_id, forum=forum, first_post__moderation_state="OK")

    if post_id:
        post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug)
        quote = loader.render_to_string('forum/quote_style.html', {'post':post})
    else:
        post = None
        quote = ""
    
    latest_posts = Post.objects.select_related('author', 'author__profile', 'thread', 'thread__forum').order_by('-created').filter(thread=thread, moderation_state="OK")[0:15]
    user_can_post_in_forum = request.user.profile.can_post_in_forum()

    if request.method == 'POST':
        form = PostReplyForm(request, quote, request.POST)

        if user_can_post_in_forum[0]:
            if form.is_valid():
                if not request.user.post_set.all().count() and ("http://" in form.cleaned_data["body"] or "https://" in form.cleaned_data["body"]): # first post has urls
                    post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread, moderation_state="NM")
                    # DO NOT add the post to solr, only do it when it is moderated
                    set_to_moderation = True
                else:
                    post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread)
                    add_post_to_solr(post)
                    set_to_moderation = False

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

                if not set_to_moderation:
                    return HttpResponseRedirect(post.get_absolute_url())
                else:
                    messages.add_message(request, messages.INFO, "Your post won't be shown until it is manually approved by moderators")
                    return HttpResponseRedirect(post.thread.get_absolute_url())

    else:
        if quote:
            form = PostReplyForm(request, quote, {'body':quote})
        else:
            form = PostReplyForm(request, quote)

    if not user_can_post_in_forum[0]:
        messages.add_message(request, messages.INFO, user_can_post_in_forum[1])

    return render_to_response('forum/reply.html', locals(), context_instance=RequestContext(request))


@login_required
def new_thread(request, forum_name_slug):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    user_can_post_in_forum = request.user.profile.can_post_in_forum()

    if request.method == 'POST':
        form = NewThreadForm(request.POST)
        if user_can_post_in_forum[0]:
            if form.is_valid():
                thread = Thread.objects.create(forum=forum, author=request.user, title=form.cleaned_data["title"])
                if not request.user.post_set.all().count() and ("http://" in form.cleaned_data["body"] or "https://" in form.cleaned_data["body"]): # first post has urls
                    post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread, moderation_state="NM")
                    # DO NOT add the post to solr, only do it when it is moderated
                    set_to_moderation = True
                else:
                    post = Post.objects.create(author=request.user, body=form.cleaned_data['body'], thread=thread)
                    add_post_to_solr(post)
                    set_to_moderation = False

                # Add first post to thread (this will never be changed)
                thread.first_post = post
                thread.save()

                if form.cleaned_data["subscribe"]:
                    Subscription.objects.create(subscriber=request.user, thread=thread, is_active=True)

                if not set_to_moderation:
                    return HttpResponseRedirect(post.get_absolute_url())
                else:
                    messages.add_message(request, messages.INFO, "Your post won't be shown until it is manually approved by moderators")
                    return HttpResponseRedirect(post.thread.forum.get_absolute_url())
    else:
        form = NewThreadForm()

    if not user_can_post_in_forum[0]:
        messages.add_message(request, messages.INFO, user_can_post_in_forum[1])

    return render_to_response('forum/new_thread.html', locals(), context_instance=RequestContext(request))


@login_required
def unsubscribe_from_thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id, first_post__moderation_state="OK")
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