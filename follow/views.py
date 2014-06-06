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

from django.http import HttpResponse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
import follow.utils
from follow.models import FollowingUserItem
from follow.models import FollowingQueryItem
from django.contrib.auth.models import User
from django.shortcuts import redirect, render_to_response
from datetime import datetime, timedelta
from search.views import search_prepare_query, search_prepare_sort
import settings
from freesound.utils.search.solr import Solr, SolrResponseInterpreter
from search.forms import SEARCH_SORT_OPTIONS_WEB
# from utils.search.solr import Solr, SolrQuery, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
from collections import OrderedDict
from django.core.urlresolvers import reverse

@login_required
def follow_user(request, username):
    # create following user item relation
    user_from = request.user
    user_to = User.objects.get(username=username)
    fui = FollowingUserItem(user_from=user_from, user_to=user_to)
    fui.save()
    return HttpResponse()

@login_required
def unfollow_user(request, username):
    user_from = request.user
    user_to = User.objects.get(username=username)
    FollowingUserItem.objects.get(user_from=user_from, user_to=user_to).delete()
    return HttpResponse()

@login_required
def follow_tags(request, slash_tags):
    user = request.user
    space_tags = slash_tags.replace("/", " ")
    FollowingQueryItem(user=user, query=space_tags).save()
    return HttpResponse()

@login_required
def unfollow_tags(request, slash_tags):
    user = request.user
    space_tags = slash_tags.replace("/", " ")
    FollowingQueryItem.objects.get(user=user, query=space_tags).delete()
    return HttpResponse()

@login_required
def stream(request):

    SELECT_OPTIONS = OrderedDict([
        ("last_week", "Last week"),
        ("last_month", "Last month"),
        ("specific_dates", "Specify dates...")
    ])

    SELECT_OPTIONS_DAYS = {
        "last_week": 7,
        "last_month": 30,
        "specific_dates": 0
    }

    SOLR_QUERY_LIMIT_PARAM = 3

    user = request.user

    if request.method == "POST":
        select_value = request.POST.get("time_lapse")
        if select_value == "specific_dates":
            date_from = request.POST.get("date_from")
            date_to = request.POST.get("date_to")
            time_lapse = "[%sT00:00:00Z TO %sT23:59:59.999Z]" % (date_from, date_to)
        else:
            time_lapse_day_int = SELECT_OPTIONS_DAYS[select_value]
            time_lapse = "[NOW-%sDAY TO NOW]" % str(time_lapse_day_int)
    else:
        time_lapse_day_int = SELECT_OPTIONS_DAYS["last_week"]
        time_lapse = "[NOW-%sDAY TO NOW]" % str(time_lapse_day_int)

    # print time_lapse

    solr = Solr(settings.SOLR_URL)

    sort_str = search_prepare_sort("created desc", SEARCH_SORT_OPTIONS_WEB)

    #
    # USERS FOLLOWING
    #

    users_following = follow.utils.get_users_following(user)

    users_sound_ids = []
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
        more_count = result.num_found - SOLR_QUERY_LIMIT_PARAM
        base_url = reverse("sounds-search")
        more_url = base_url + "?f=" + filter_str + "&s=" + sort_str[0]

        if result.num_rows != 0:
            sound_ids = [element['id'] for element in result.docs]
            users_sound_ids.append(((user_following, False), more_count, more_url, sound_ids))

    # print users_sound_ids

    #
    # TAGS FOLLOWING
    #

    tags_following = follow.utils.get_tags_following(user)

    tags_sound_ids = []

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
        more_count = result.num_found - SOLR_QUERY_LIMIT_PARAM
        base_url = reverse("sounds-search")
        more_url = base_url + "?f=" + tag_filter_str + "&s=" + sort_str[0]

        if result.num_rows != 0:
            sound_ids = [element['id'] for element in result.docs]
            tags_sound_ids.append((tags, more_count, more_url, sound_ids))

    # print tags_sound_ids

    return render_to_response('follow/stream.html', locals(), context_instance=RequestContext(request))