#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


import datetime
import re
import functools

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, Http404, HttpResponsePermanentRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.urls import reverse
from django.db import transaction

from accounts.models import DeletedUser
from forum.forms import PostReplyForm, NewThreadForm, PostModerationForm
from forum.models import Forum, Thread, Post, Subscription
from utils.cache import invalidate_template_cache, invalidate_all_moderators_header_cache
from utils.mail import send_mail_template
from utils.pagination import paginate
from utils.search.search_forum import add_posts_to_search_engine
from utils.text import text_may_be_spam, remove_control_chars


def deactivate_spammer(user_id):
    from django.contrib.auth.models import User
    from django.contrib.sessions.models import Session
    user = User.objects.get(id=user_id)
    Post.objects.filter(author=user).delete()
    Thread.objects.filter(author=user).delete()
    [s.delete() for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == user.id]
    user.is_active = False
    user.save()


def last_action(view_func):

    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

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

        reply_object = view_func(request, *args, **kwargs)

        reply_object.set_cookie(key, now_as_string, 60*60*24*30)  # 30 days

        return reply_object

    return inner


@last_action
def forums(request):
    forums = Forum.objects.select_related(
        'last_post', 'last_post__author', 'last_post__author__profile', 'last_post__thread').all()
    tvars = {'forums': forums}
    return render(request, 'forum/index.html', tvars)


@last_action
def forum(request, forum_name_slug):
    try:
        forum = Forum.objects.get(name_slug=forum_name_slug)
    except Forum.DoesNotExist:
        raise Http404

    tvars = {'forum': forum}
    paginator = paginate(request, Thread.objects.filter(forum=forum, first_post__moderation_state="OK")
                         .select_related('last_post', 'last_post__author', 'last_post__author__profile',
                                         'author', 'author__profile', 'first_post', 'forum'),
                         settings.FORUM_THREADS_PER_PAGE)
    tvars.update(paginator)

    return render(request, 'forum/threads.html', tvars)


@last_action
@transaction.atomic()
def thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread.objects.select_related('last_post', 'last_post__author'),
                               forum=forum, id=thread_id, first_post__moderation_state="OK")

    paginator = paginate(request, Post.objects.select_related(
        'author', 'author__profile', 'thread', 'thread__forum',
    ).filter(
        thread=thread, moderation_state="OK"), settings.FORUM_POSTS_PER_PAGE)

    has_subscription = False
    # a logged in user watching a thread can activate his subscription to that thread!
    # we assume the user has seen the latest post if he is browsing the thread
    # this is not entirely correct, but should be close enough
    if request.user.is_authenticated:
        try:
            subscription = Subscription.objects.get(thread=thread, subscriber=request.user)
            if not subscription.is_active:
                subscription.is_active = True
                subscription.save()
            has_subscription = True
        except Subscription.DoesNotExist:
            pass

    tvars = {'thread': thread,
             'forum': forum,
             'post_counter_offset': settings.FORUM_POSTS_PER_PAGE * (paginator['current_page'] - 1),  # Only used in BW
             'has_subscription': has_subscription}
    tvars.update(paginator)
    return render(request, 'forum/thread.html', tvars)


@last_action
def latest_posts(request):
    # The "latest posts" page no longet exists, we now redirect to "hot threads"
    return HttpResponseRedirect(reverse('forums-hot-threads'))


def get_hot_threads(n=None, days=15):
    if not settings.DEBUG:
        last_days_filter = datetime.datetime.today() - datetime.timedelta(days=days)
    else:
        # If in DEBUG mode we won't have recent posts, so we modify the filter to match all existing threads
        last_days_filter = Post.objects.order_by('created').first().created
    return Thread.objects.filter(first_post__moderation_state="OK",
                                 last_post__moderation_state="OK",
                                 last_post__created__gte=last_days_filter) \
               .order_by('-last_post__created') \
               .select_related('author',
                               'forum',
                               'last_post',
                               'last_post__author',
                               'last_post__thread',
                               'last_post__thread__forum')[:n]


def hot_threads(request):
    paginator = paginate(request, get_hot_threads(), settings.FORUM_THREADS_PER_PAGE)
    tvars = {}
    tvars.update(paginator)
    return render(request, 'forum/hot_threads.html', tvars)


@last_action
def post(request, forum_name_slug, thread_id, post_id):
    post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug,
                             moderation_state="OK")

    posts_before = Post.objects.filter(thread=post.thread, moderation_state="OK", created__lt=post.created).count()
    page = 1 + (posts_before // settings.FORUM_POSTS_PER_PAGE)
    url = post.thread.get_absolute_url() + "?page=%d#post%d" % (page, post.id)

    return HttpResponseRedirect(url)


@login_required
@transaction.atomic()
def reply(request, forum_name_slug, thread_id, post_id=None):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, id=thread_id, forum=forum, first_post__moderation_state="OK")

    if post_id:
        post = get_object_or_404(Post, id=post_id, thread__id=thread_id, thread__forum__name_slug=forum_name_slug)
        quote = loader.render_to_string('forum/quote_style.html', {'post': post})
    else:
        post = None
        quote = ""

    latest_posts = Post.objects.select_related('author', 'author__profile', 'thread', 'thread__forum')\
                       .order_by('-created').filter(thread=thread, moderation_state="OK")[0:15]
    user_can_post_in_forum, user_can_post_message = request.user.profile.can_post_in_forum()
    user_is_blocked_for_spam_reports = request.user.profile.is_blocked_for_spam_reports()
    FromToUse = PostReplyForm

    if request.method == 'POST':
        form = FromToUse(request, quote, request.POST)

        if user_can_post_in_forum and not user_is_blocked_for_spam_reports:
            if form.is_valid():
                may_be_spam = text_may_be_spam(form.cleaned_data.get("body", '')) or \
                              text_may_be_spam(form.cleaned_data.get("title", ''))
                if not request.user.posts.filter(moderation_state="OK").count() and may_be_spam:
                    post = Post.objects.create(
                        author=request.user, body=form.cleaned_data["body"], thread=thread, moderation_state="NM")
                    # DO NOT add the post to the search engine, only do it when it is moderated
                    set_to_moderation = True
                else:
                    post = Post.objects.create(author=request.user, body=form.cleaned_data["body"], thread=thread)
                    add_posts_to_search_engine([post])
                    set_to_moderation = False

                if form.cleaned_data["subscribe"]:
                    subscription, created = Subscription.objects.get_or_create(thread=thread, subscriber=request.user)
                    if not subscription.is_active:
                        subscription.is_active = True
                        subscription.save()
                else:
                    # If "subscribe" not in form, then remove subscription (if any is existing)
                    Subscription.objects.filter(thread=thread, subscriber=request.user).delete()

                # Invalidate the thread common commenters cache as it could have changed
                invalidate_template_cache('bw_thread_common_commenters', thread.id)

                # figure out if there are active subscriptions in this thread
                if not set_to_moderation:
                    users_to_notify = []
                    for subscription in Subscription.objects\
                            .filter(thread=thread, is_active=True).exclude(subscriber=request.user):
                        users_to_notify.append(subscription.subscriber)
                        subscription.is_active = False
                        subscription.save()

                    if users_to_notify and post.thread.get_status_display() != 'Sunk':
                        send_mail_template(
                            settings.EMAIL_SUBJECT_TOPIC_REPLY,
                            "emails/email_new_post_notification.txt",
                            {'post': post, 'thread': thread, 'forum': forum},
                            extra_subject=thread.title,
                            user_to=users_to_notify, email_type_preference_check="new_post"
                        )

                if not set_to_moderation:
                    return HttpResponseRedirect(post.get_absolute_url())
                else:
                    messages.add_message(request, messages.INFO, "Your post won't be shown until it is manually "
                                                                 "approved by moderators")
                    return HttpResponseRedirect(post.thread.get_absolute_url())
    else:
        initial = {'subscribe': thread.is_user_subscribed(request.user)}
        if quote:
            initial.update({'body': quote})
        form = FromToUse(request, quote, initial=initial)

    if not user_can_post_in_forum:
        messages.add_message(request, messages.INFO, user_can_post_message)

    if user_is_blocked_for_spam_reports:
        messages.add_message(request, messages.INFO, "You're not allowed to post in the forums because your account "
                                                     "has been temporaly blocked after multiple spam reports")

    tvars = {'forum': forum,
             'thread': thread,
             'form': form,
             'latest_posts': latest_posts}
    return render(request, 'forum/reply.html', tvars)


@login_required
@transaction.atomic()
def new_thread(request, forum_name_slug):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    user_can_post_in_forum, user_can_post_message = request.user.profile.can_post_in_forum()
    user_is_blocked_for_spam_reports = request.user.profile.is_blocked_for_spam_reports()
    FormToUse = NewThreadForm

    if request.method == 'POST':
        form = FormToUse(request.POST)
        if user_can_post_in_forum and not user_is_blocked_for_spam_reports:
            if form.is_valid():
                post_title = form.cleaned_data["title"]
                post_body = form.cleaned_data["body"]
                thread = Thread.objects.create(forum=forum, author=request.user, title=post_title)
                may_be_spam = text_may_be_spam(post_body) or \
                              text_may_be_spam(post_title)

                post_body = remove_control_chars(post_body)
                if not request.user.posts.filter(moderation_state="OK").count() and may_be_spam:
                    post = Post.objects.create(author=request.user, body=post_body, thread=thread,
                                               moderation_state="NM")
                    # DO NOT add the post to the search engine, only do it when it is moderated
                    set_to_moderation = True
                else:
                    post = Post.objects.create(author=request.user, body=post_body, thread=thread)
                    add_posts_to_search_engine([post])
                    set_to_moderation = False

                # Add first post to thread (first post will always be the same)
                # We need to reload thread object from DB, not so overwrite the object we created before when saving
                # TODO: Ideally we would have a specific function to create a Post and add it to a thread immediately
                #       so that we can use this functionality in tests too
                updated_thread = Thread.objects.get(id=thread.id)
                updated_thread.first_post = post
                updated_thread.save()

                if form.cleaned_data["subscribe"]:
                    Subscription.objects.create(subscriber=request.user, thread=thread, is_active=True)

                if not set_to_moderation:
                    return HttpResponseRedirect(post.get_absolute_url())
                else:
                    messages.add_message(request, messages.INFO, "Your post won't be shown until it is manually "
                                                                 "approved by moderators")
                    return HttpResponseRedirect(post.thread.forum.get_absolute_url())
    else:
        form = FormToUse()

    if not user_can_post_in_forum:
        messages.add_message(request, messages.INFO, user_can_post_message)

    if user_is_blocked_for_spam_reports:
        messages.add_message(request, messages.INFO, "You're not allowed to post in the forums because your account "
                                                     "has been temporarily blocked after multiple spam reports")

    tvars = {'forum': forum,
             'form': form}
    return render(request, 'forum/new_thread.html', tvars)


@login_required
def unsubscribe_from_thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id, first_post__moderation_state="OK")
    Subscription.objects.filter(thread=thread, subscriber=request.user).delete()
    messages.add_message(request, messages.INFO, 'You have been unsubscribed from notifications for this thread.')
    return HttpResponseRedirect(reverse('forums-thread', args=[forum.name_slug, thread.id]))


@login_required
def subscribe_to_thread(request, forum_name_slug, thread_id):
    forum = get_object_or_404(Forum, name_slug=forum_name_slug)
    thread = get_object_or_404(Thread, forum=forum, id=thread_id, first_post__moderation_state="OK")
    subscription, created = Subscription.objects.get_or_create(thread=thread, subscriber=request.user)
    messages.add_message(request, messages.INFO, "You have been subscribed to this thread. You will receive an "
                                                 "email notification every time someone makes a reply to this thread.")
    return HttpResponseRedirect(reverse('forums-thread', args=[forum.name_slug, thread.id]))


def old_topic_link_redirect(request):
    post_id = request.GET.get("p", False)
    if post_id:
        post_id = re.sub(r"\D", "", post_id)
        try:
            post = get_object_or_404(Post, id=post_id)
        except ValueError:
            raise Http404
        return HttpResponsePermanentRedirect(
            reverse('forums-post', args=[post.thread.forum.name_slug, post.thread.id, post.id]))

    thread_id = request.GET.get("t", False)
    if thread_id:
        thread_id = re.sub(r"\D", "", thread_id)
        try:
            thread = get_object_or_404(Thread, id=thread_id)
        except ValueError:
            raise Http404
        return HttpResponsePermanentRedirect(reverse('forums-thread', args=[thread.forum.name_slug, thread.id]))

    raise Http404


@login_required
def post_delete_confirm(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        if post.author == request.user or request.user.has_perm('forum.delete_post'):
            # Delete post and save reference to thread, forum and creation date (it will be used later to
            # decide to what post redirect after deletion)
            deleted_post_created = post.created
            thread = post.thread
            forum = thread.forum
            post.delete()

            # Invalidate the thread common commenters cache as it could have changed
            invalidate_template_cache('bw_thread_common_commenters', thread.id)

            # If the post was the only post in the thread, redirect to the forum
            try:
                thread.refresh_from_db()
            except Thread.DoesNotExist:
                return redirect('forums-forum', forum_name_slug=forum.name_slug)

            # Otherwise redirect to the previous post in the thread (if not previous posts, redirect to last post)
            try:
                previous_posts = thread.post_set.filter(created__lte=deleted_post_created).order_by('-created')
                if previous_posts.count():
                    return redirect('forums-post', thread.forum.name_slug, thread.id, previous_posts[0].id)
                else:
                    return redirect('forums-post', thread.forum.name_slug, thread.id, thread.last_post_id)
            except (Post.DoesNotExist, Thread.DoesNotExist, AttributeError):
                return HttpResponseRedirect(reverse('forums-forums'))

    raise Http404


@login_required
@transaction.atomic()
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    FromToUse = PostReplyForm
    if post.author == request.user or request.user.has_perm('forum.change_post'):
        if request.method == 'POST':
            form = FromToUse(request, '', request.POST)
            if form.is_valid():
                post.body = remove_control_chars(form.cleaned_data['body'])
                post.save()
                add_posts_to_search_engine([post])

                if form.cleaned_data["subscribe"]:
                    subscription, created = Subscription.objects.get_or_create(thread=post.thread,
                                                                               subscriber=request.user)
                    if not subscription.is_active:
                        subscription.is_active = True
                        subscription.save()
                else:
                    # If "subscribe" not in form, then remove subscription (if any is existing)
                    Subscription.objects.filter(thread=post.thread, subscriber=request.user).delete()

                return HttpResponseRedirect(
                    reverse('forums-post', args=[post.thread.forum.name_slug, post.thread.id, post.id]))
        else:
            initial = {
                'subscribe': post.thread.is_user_subscribed(request.user),
                'body': post.body
            }
            form = FromToUse(request, '', initial=initial)

        latest_posts = Post.objects.select_related('author', 'author__profile', 'thread', 'thread__forum') \
                           .order_by('-created') \
                           .filter(thread=post.thread, moderation_state="OK", created__lt=post.created)[0:15]
        tvars = {'forum': post.thread.forum,
                 'thread': post.thread,
                 'form': form,
                 'latest_posts': latest_posts,
                 'editing': True}
        return render(request, 'forum/reply.html', tvars)
    else:
        raise Http404


@permission_required('forum.can_moderate_forum')
@transaction.atomic()
def moderate_posts(request):
    PostModerationFormClass = PostModerationForm
    if request.method == 'POST':
        
        # Only the form for one post will be sent at a time, but we need to get the post ID from the request so we know which form prefix to use
        post_id = -1
        for key in request.POST.keys():
            if key.endswith('-post'):
                post_id = int(key.split('-')[0])
        
        mod_form = PostModerationFormClass(request.POST, prefix=f'{post_id}')
        if mod_form.is_valid():
            action = mod_form.cleaned_data.get("action")
            post_id = mod_form.cleaned_data.get("post")
            try:
                post = Post.objects.get(id=post_id)
                if action == "Approve":
                    post.moderation_state = "OK"
                    post.save()

                    # Invalidate the thread common commenters cache as it could have changed
                    invalidate_template_cache('bw_thread_common_commenters', post.thread.id)

                elif action == "Delete User":
                    try:
                        deletion_reason = DeletedUser.DELETION_REASON_SPAMMER
                        post.author.profile.delete_user(delete_user_object_from_db=True,
                                                        deletion_reason=deletion_reason)
                        messages.add_message(request, messages.INFO, 'The user has been successfully deleted.')
                    except User.DoesNotExist:
                        messages.add_message(request, messages.INFO, 'The user has already been deleted.')
                elif action == "Delete Post":
                    post.delete()
                    messages.add_message(request, messages.INFO, 'The post has been successfully deleted.')
            except Post.DoesNotExist:
                messages.add_message(request, messages.INFO, 'This post no longer exists. It may have already been deleted.')

            invalidate_all_moderators_header_cache()

    pending_posts = Post.objects.filter(moderation_state='NM').select_related('author', 'author__profile')
    post_list = []
    for p in pending_posts:
        f = PostModerationFormClass(initial={'action': 'Approve', 'post': p.id}, prefix=f'{p.id}')
        post_list.append({'post': p, 'form': f})

    tvars = {'post_list': post_list,
             'hide_search': True}
    return render(request, 'forum/moderate.html', tvars)
