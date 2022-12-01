# -*- coding: utf-8 -*-

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

from future import standard_library
standard_library.install_aliases()
from follow.models import FollowingUserItem, FollowingQueryItem
import sounds
from utils.search import get_search_engine
import urllib.request, urllib.parse, urllib.error
from django.conf import settings


def get_users_following_qs(user):
    return FollowingUserItem.objects.select_related('user_to__profile')\
        .filter(user_from=user).order_by('user_to__username')


def get_users_following(user):
    return [item.user_to for item in get_users_following_qs(user)]


def get_users_followers_qs(user):
    return FollowingUserItem.objects.select_related('user_from__profile')\
        .filter(user_to=user).order_by('user_from__username')


def get_users_followers(user):
    return [item.user_from for item in get_users_followers_qs(user)]


def get_tags_following_qs(user):
    return FollowingQueryItem.objects.filter(user=user).order_by('query')


def get_tags_following(user):
    return [item.query for item in get_tags_following_qs(user)]


def is_user_following_user(user_from, user_to):
    return FollowingUserItem.objects.filter(user_from=user_from, user_to=user_to).exists()


def is_user_following_tag(user, slash_tag):
    return FollowingQueryItem.objects.filter(user=user, query=slash_tag.replace("/", " ")).exists()


def get_stream_sounds(user, time_lapse, num_results_per_grup=3):

    search_engine = get_search_engine()

    #
    # USERS FOLLOWING
    #

    users_following = get_users_following(user)

    users_sounds = []
    for user_following in users_following:

        filter_str = "username:\"" + user_following.username + "\" created:" + time_lapse
        result = search_engine.search_sounds(
            textual_query='',
            query_filter=filter_str,
            sort=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
            offset=0,
            num_sounds=num_results_per_grup,
            group_by_pack=False,
        )

        if result.num_rows != 0:

            more_count = max(0, result.num_found - num_results_per_grup)

            # the sorting only works if done like this!
            more_url_params = [urllib.parse.quote(filter_str), urllib.parse.quote(settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST)]

            # this is the same link but for the email has to be "quoted"
            more_url = u"?f=" + filter_str + u"&s=" + settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST
            # more_url_quoted = urllib.quote(more_url)

            sound_ids = [element['id'] for element in result.docs]
            sound_objs = sounds.models.Sound.objects.filter(id__in=sound_ids).select_related('license', 'user')
            new_count = more_count + len(sound_ids)
            users_sounds.append(((user_following, False), sound_objs, more_url_params, more_count, new_count))

    #
    # TAGS FOLLOWING
    #

    tags_following = get_tags_following(user)

    tags_sounds = []
    for tag_following in tags_following:

        tags = tag_following.split(" ")
        tag_filter_query = ""
        for tag in tags:
            tag_filter_query += "tag:" + tag + " "

        tag_filter_str = tag_filter_query + " created:" + time_lapse

        result = search_engine.search_sounds(
            textual_query='',
            query_filter=tag_filter_str,
            sort=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
            offset=0,
            num_sounds=num_results_per_grup,
            group_by_pack=False,
        )

        if result.num_rows != 0:

            more_count = max(0, result.num_found - num_results_per_grup)

            # the sorting only works if done like this!
            more_url_params = [urllib.parse.quote(tag_filter_str), urllib.parse.quote(settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST)]

            # this is the same link but for the email has to be "quoted"
            more_url = u"?f=" + tag_filter_str + u"&s=" + settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST
            # more_url_quoted = urllib.quote(more_url)

            sound_ids = [element['id'] for element in result.docs]
            sound_objs = sounds.models.Sound.objects.filter(id__in=sound_ids)
            new_count = more_count + len(sound_ids)
            tags_sounds.append((tags, sound_objs, more_url_params, more_count, new_count))

    return users_sounds, tags_sounds


def build_time_lapse(date_from, date_to):
    date_from = date_from.strftime("%Y-%m-%d")
    date_to = date_to.strftime("%Y-%m-%d")
    time_lapse = '["%sT00:00:00Z" TO "%sT23:59:59.999Z"]' % (date_from, date_to)
    return time_lapse

