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
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext

import accounts.views as accounts

from django.contrib.auth.decorators import login_required
from follow.models import FollowingUserItem
from follow.models import FollowingQueryItem
from django.contrib.auth.models import User
from django.shortcuts import redirect, render_to_response
import django.utils.http as utils

from datetime import datetime, timedelta
import follow.utils
from sounds.models import Sound


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

    user = request.user

    # following_users = follow.utils.get_users_following(user)
    #
    # # TODO: change this to the form input
    # start_date = datetime.now()
    # end_date = start_date - timedelta(days=7)
    #
    # # TODO: which field to use for the query?
    # # analysis_state
    # # created
    # # moderation_date
    # # moderation_state
    # # processing_date
    # # processing_state
    # solr = Solr(settings.SOLR_URL)
    # query = search_prepare_query("",
    #                              "username:Jovica created:[1976-03-06T00:00:00.999Z TO *]", # tag:tag1 tag:tag2 ... created:sdfsdf
    #                              "created desc",
    #                              1,
    #                              5,
    #                              grouping=False,
    #                              include_facets=False)
    #
    # result = SolrResponseInterpreter(solr.select(unicode(query)))
    # solr_ids = [element['id'] for element in result.docs]
    #
    # sounds = Sound.objects.filter(user__in=following_users, created__range=(start_date, end_date))
    #
    # Sound.objects.filter(user__in=following_users)

    return render_to_response('follow/stream.html', locals(), context_instance=RequestContext(request))