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

from follow.models import FollowingUserItem, FollowingQueryItem
import sounds
from search.views import search_prepare_query, search_prepare_sort
from django.conf import settings
from utils.search.solr import Solr, SolrResponseInterpreter
from search.forms import SEARCH_SORT_OPTIONS_WEB
# from utils.search.solr import Solr, SolrQuery, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
import urllib

SOLR_QUERY_LIMIT_PARAM = 3


def get_users_following(user):
    items = FollowingUserItem.objects.select_related('user_to__profile').filter(user_from=user)
    return [item.user_to for item in items]


def get_users_followers(user):
    items = FollowingUserItem.objects.select_related('user_from__profile').filter(user_to=user)
    return [item.user_from for item in items]


def get_tags_following(user):
    items = FollowingQueryItem.objects.filter(user=user)
    return [item.query for item in items]


def is_user_following_user(user_from, user_to):
    return user_to in get_users_following(user=user_from)


def is_user_following_tag(user, slash_tag):
    tags_following = get_tags_following(user)
    space_tag = slash_tag.replace("/", " ")
    return space_tag in tags_following


def is_user_being_followed_by_user(user_from, user_to):
    return user_to in get_users_followers(user_from)


def get_vars_for_account_view(user):
    return get_vars_for_views_helper(user, clip=True)


def get_vars_for_home_view(user):
    return get_vars_for_views_helper(user, clip=False)


def get_vars_for_views_helper(user, clip):

    following = get_users_following(user)
    followers = get_users_followers(user)
    following_tags = get_tags_following(user)

    following_count = len(following)
    followers_count = len(followers)
    following_tags_count = len(following_tags)

    # show only the first 21 (3 rows) followers and following users and 5 following tags
    if clip:
        following = following[:21]
        followers = followers[:21]
        following_tags = following_tags[:5]

    space_tags = following_tags
    split_tags = [tag.split(" ") for tag in space_tags]
    slash_tags = [tag.replace(" ", "/") for tag in space_tags]

    following_tags = []
    for i in range(len(space_tags)):
        following_tags.append((space_tags[i], slash_tags[i], split_tags[i]))

    return following, followers, following_tags, following_count, followers_count, following_tags_count


def get_stream_sounds(user, time_lapse):

    solr = Solr(settings.SOLR_URL)

    sort_str = search_prepare_sort("created desc", SEARCH_SORT_OPTIONS_WEB)

    #
    # USERS FOLLOWING
    #

    users_following = get_users_following(user)

    users_sounds = []
    for user_following in users_following:

        filter_str = "username:" + user_following.username + " created:" + time_lapse

        query = search_prepare_query(
            "",
            filter_str,
            sort_str,
            1,
            SOLR_QUERY_LIMIT_PARAM,
            grouping=False,
            include_facets=False
        )

        result = SolrResponseInterpreter(solr.select(unicode(query)))

        if result.num_rows != 0:

            more_count = max(0, result.num_found - SOLR_QUERY_LIMIT_PARAM)

            # the sorting only works if done like this!
            more_url_params = [urllib.quote(filter_str), urllib.quote(sort_str[0])]

            # this is the same link but for the email has to be "quoted"
            more_url = u"?f=" + filter_str + u"&s=" + sort_str[0]
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

        query = search_prepare_query(
            "",
            tag_filter_str,
            sort_str,
            1,
            SOLR_QUERY_LIMIT_PARAM,
            grouping=False,
            include_facets=False
        )

        result = SolrResponseInterpreter(solr.select(unicode(query)))

        if result.num_rows != 0:

            more_count = max(0, result.num_found - SOLR_QUERY_LIMIT_PARAM)

            # the sorting only works if done like this!
            more_url_params = [urllib.quote(tag_filter_str), urllib.quote(sort_str[0])]

            # this is the same link but for the email has to be "quoted"
            more_url = u"?f=" + tag_filter_str + u"&s=" + sort_str[0]
            # more_url_quoted = urllib.quote(more_url)

            sound_ids = [element['id'] for element in result.docs]
            sound_objs = sounds.models.Sound.objects.filter(id__in=sound_ids)
            new_count = more_count + len(sound_ids)
            tags_sounds.append((tags, sound_objs, more_url_params, more_count, new_count))

    return users_sounds, tags_sounds


def build_time_lapse(date_from, date_to):
    date_from = date_from.strftime("%Y-%m-%d")
    date_to = date_to.strftime("%Y-%m-%d")
    time_lapse = "[%sT00:00:00Z TO %sT23:59:59.999Z]" % (date_from, date_to)
    return time_lapse

