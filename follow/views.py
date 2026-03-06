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
from collections import OrderedDict
from socket import error as socket_error

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from follow import follow_utils
from follow.models import FollowingQueryItem, FollowingUserItem
from utils.cache import invalidate_user_template_caches
from utils.pagination import paginate
from utils.username import get_parameter_user_or_404, raise_404_if_user_is_deleted, redirect_if_old_username


@redirect_if_old_username
@raise_404_if_user_is_deleted
def following_users(request, username):
    """List of users that are being followed by user with "username" """
    if not request.GET.get("ajax"):
        # If not loaded as a modal, redirect to account page with parameter to open modal
        return HttpResponseRedirect(reverse("account", args=[username]) + "?following=1")

    user = get_parameter_user_or_404(request)
    following = follow_utils.get_users_following_qs(user)
    tvars = {"user": user}

    # NOTE: 'next_path' tvar below is used for follow/unfollow buttons. We overwrite default value of next_path
    # given by the context processor so the redirects go to the user profile page URL instead of the follow modal
    # body content URL
    paginator = paginate(request, following, settings.FOLLOW_ITEMS_PER_PAGE)
    tvars.update(paginator)
    tvars.update(
        {
            "next_path": reverse("account", args=[username]) + f"?following={paginator['current_page']}",
            "follow_page": "following",
        }
    )
    return render(request, "accounts/modal_follow.html", tvars)


@redirect_if_old_username
@raise_404_if_user_is_deleted
def followers(request, username):
    """List of users that are following user with "username" """
    if not request.GET.get("ajax"):
        # If not loaded as a modal, redirect to account page with parameter to open modal
        return HttpResponseRedirect(reverse("account", args=[username]) + "?followers=1")

    user = get_parameter_user_or_404(request)
    followers = follow_utils.get_users_followers_qs(user)
    tvars = {"user": user}

    # NOTE: 'next_path' tvar below is used for follow/unfollow buttons. We overwrite default value of next_path
    # given by the context processor so the redirects go to the user profile page URL instead of the follow modal
    # body content URL
    paginator = paginate(request, followers, settings.FOLLOW_ITEMS_PER_PAGE)
    tvars.update(paginator)
    tvars.update(
        {
            "next_path": reverse("account", args=[username]) + f"?followers={paginator['current_page']}",
            "follow_page": "followers",
        }
    )
    return render(request, "accounts/modal_follow.html", tvars)


@redirect_if_old_username
@raise_404_if_user_is_deleted
def following_tags(request, username):
    """List of tags that are being followed by user with "username" """
    if not request.GET.get("ajax"):
        # If not loaded as a modal, redirect to account page with parameter to open modal
        return HttpResponseRedirect(reverse("account", args=[username]) + "?followingTags=1")

    user = get_parameter_user_or_404(request)
    following_tags = follow_utils.get_tags_following_qs(user)
    tvars = {
        "user": user,
    }
    # NOTE: 'next_path' tvar below is used for follow/unfollow buttons. We overwrite default value of next_path
    # given by the context processor so the redirects go to the user profile page URL instead of the follow modal
    # body content URL
    paginator = paginate(request, following_tags, settings.FOLLOW_ITEMS_PER_PAGE)
    tvars.update(paginator)
    tvars.update(
        {
            "next_path": reverse("account", args=[username]) + f"?followingTags={paginator['current_page']}",
            "follow_page": "tags",  # Used in BW
        }
    )
    return render(request, "accounts/modal_follow.html", tvars)


@login_required
def follow_user(request, username):
    # create following user item relation
    user_from = request.user
    user_to = get_object_or_404(User, username=username)
    FollowingUserItem.objects.get_or_create(user_from=user_from, user_to=user_to)
    invalidate_user_template_caches(user_from.id)
    invalidate_user_template_caches(user_to.id)

    # Check if there's next parameter, and if there is we redirect to it
    # This is to implement follow/unfollow without Javascript
    redirect_to = request.GET.get("next", None)
    if redirect_to is not None:
        return HttpResponseRedirect(redirect_to)

    return HttpResponse()


@login_required
def unfollow_user(request, username):
    user_from = request.user
    user_to = get_object_or_404(User, username=username)
    try:
        FollowingUserItem.objects.get(user_from=user_from, user_to=user_to).delete()
        invalidate_user_template_caches(user_from.id)
        invalidate_user_template_caches(user_to.id)
    except FollowingUserItem.DoesNotExist:
        # If the relation does not exist we're fine, should have never got to here...
        pass

    # Check if there's next parameter, and if there is we redirect to it
    # This is to implement follow/unfollow without Javascript
    redirect_to = request.GET.get("next", None)
    if redirect_to is not None:
        return HttpResponseRedirect(redirect_to)

    return HttpResponse()


@login_required
def follow_tags(request, slash_tags):
    user = request.user
    space_tags = slash_tags.replace("/", " ")
    FollowingQueryItem.objects.get_or_create(user=user, query=space_tags)
    invalidate_user_template_caches(user.id)

    # Check if there's next parameter, and if there is we redirect to it
    # This is to implement follow/unfollow without Javascript
    redirect_to = request.GET.get("next", None)
    if redirect_to is not None:
        return HttpResponseRedirect(redirect_to)

    return HttpResponse()


@login_required
def unfollow_tags(request, slash_tags):
    user = request.user
    space_tags = slash_tags.replace("/", " ")
    try:
        FollowingQueryItem.objects.get(user=user, query=space_tags).delete()
        invalidate_user_template_caches(user.id)
    except FollowingQueryItem.DoesNotExist:
        # If the relation does not exist we're fine, should have never got to here...
        pass

    # Check if there's next parameter, and if there is we redirect to it
    # This is to implement follow/unfollow without Javascript
    redirect_to = request.GET.get("next", None)
    if redirect_to is not None:
        return HttpResponseRedirect(redirect_to)

    return HttpResponse()


@login_required
@transaction.atomic()
def stream(request):
    SELECT_OPTIONS = OrderedDict(
        [("last_week", "Last week"), ("last_month", "Last month"), ("specific_dates", "Specific dates...")]
    )

    SELECT_OPTIONS_DAYS = {"last_week": 7, "last_month": 30, "specific_dates": 0}

    user = request.user

    if request.method == "POST":
        select_value = request.POST.get("time_lapse")
        if select_value != "specific_dates":
            date_from = timezone.now() - datetime.timedelta(days=SELECT_OPTIONS_DAYS[select_value])
            date_to = timezone.now()
            time_lapse = follow_utils.build_time_lapse(date_from, date_to)
            date_to = date_to.strftime("%Y-%m-%d")
            date_from = date_from.strftime("%Y-%m-%d")
        else:
            date_from = request.POST.get("date_from")
            date_to = request.POST.get("date_to")
            if not date_from or not date_to:
                if not date_from and not date_to:  # Set it to last week (default)
                    date_to = timezone.now().strftime("%Y-%m-%d")
                    date_from = (timezone.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                else:
                    if not date_from:
                        date_from = (
                            datetime.datetime.strptime(date_to, "%Y-%m-%d") - datetime.timedelta(days=7)
                        ).strftime("%Y-%m-%d")  # A week before date to
                    if not date_to:
                        date_to = (
                            datetime.datetime.strptime(date_from, "%Y-%m-%d") + datetime.timedelta(days=7)
                        ).strftime("%Y-%m-%d")  # A week after date from
            time_lapse = f'["{date_from}T00:00:00Z" TO "{date_to}T23:59:59.999Z"]'

    # if first time going into the page, the default is last week
    else:
        select_value = ""
        date_from = timezone.now() - datetime.timedelta(days=SELECT_OPTIONS_DAYS["last_week"])
        date_to = timezone.now()
        time_lapse = follow_utils.build_time_lapse(date_from, date_to)
        date_to = date_to.strftime("%Y-%m-%d")
        date_from = date_from.strftime("%Y-%m-%d")

    errors_getting_data = False
    try:
        users_sounds, tags_sounds = follow_utils.get_stream_sounds(user, time_lapse, num_results_per_group=4)
    except socket_error:
        # Could not connect to solr
        errors_getting_data = True
        users_sounds = list()
        tags_sounds = list()

    tvars = {
        "SELECT_OPTIONS": SELECT_OPTIONS,
        "date_to": date_to,
        "date_from": date_from,
        "select_value": select_value,
        "errors_getting_data": errors_getting_data,
        "users_sounds": users_sounds,
        "tags_sounds": tags_sounds,
    }
    return render(request, "follow/stream.html", tvars)
