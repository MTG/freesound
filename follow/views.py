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
from follow import follow_utils
from follow.models import FollowingUserItem
from follow.models import FollowingQueryItem
from django.contrib.auth.models import User
from django.shortcuts import redirect, render_to_response
from datetime import datetime, timedelta
#from search.views import search_prepare_query, search_prepare_sort
#from django.conf import settings
#from utils.search.solr import Solr, SolrResponseInterpreter
#from search.forms import SEARCH_SORT_OPTIONS_WEB
# from utils.search.solr import Solr, SolrQuery, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
from collections import OrderedDict
#from django.core.urlresolvers import reverse

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

    user = request.user

    if request.method == "POST":
        select_value = request.POST.get("time_lapse")
        if select_value != "specific_dates":
            date_from = datetime.now() - timedelta(days=SELECT_OPTIONS_DAYS[select_value])
            date_to = datetime.now()
            time_lapse = follow_utils.build_time_lapse(date_from, date_to)
            date_to = date_to.strftime("%Y-%m-%d")
            date_from = date_from.strftime("%Y-%m-%d")
        else:
            date_from = request.POST.get("date_from")
            date_to = request.POST.get("date_to")
            if not date_from or not date_to:
                if not date_from and not date_to: # Set it to last week (default)
                    date_to = datetime.now().strftime("%Y-%m-%d")
                    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                else:
                    if not date_from:
                        date_from = (datetime.strptime(date_to,"%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d") # A week before date to
                    if not date_to:
                        date_to = (datetime.strptime(date_from,"%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d") # A week after date from
            time_lapse = "[%sT00:00:00Z TO %sT23:59:59.999Z]" % (date_from, date_to)

    # if first time going into the page, the default is last week
    else:
        date_from = datetime.now() - timedelta(days=SELECT_OPTIONS_DAYS["last_week"])
        date_to = datetime.now()
        time_lapse = follow_utils.build_time_lapse(date_from, date_to)
        date_to = date_to.strftime("%Y-%m-%d")
        date_from = date_from.strftime("%Y-%m-%d")

    errors_getting_data = False
    try:
        users_sounds, tags_sounds = follow_utils.get_stream_sounds(user, time_lapse)
    except Exception, e:
        # Could not connect to solr
        errors_getting_data = True


    return render_to_response('follow/stream.html', locals(), context_instance=RequestContext(request))