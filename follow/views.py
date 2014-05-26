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

import accounts.views as accounts

from django.contrib.auth.decorators import login_required
from follow.models import FollowingUserItem
from follow.models import FollowingQueryItem
from django.contrib.auth.models import User
from django.shortcuts import redirect
import django.utils.http as utils

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
def follow_tags(request, tags):
    user = request.user
    print "tags", tags
    FollowingQueryItem(user=user, query=tags).save()
    return HttpResponse()

@login_required
def unfollow_tags(request, tags):
    user = request.user
    FollowingQueryItem.objects.get(user=user, query=tags).delete()
    return HttpResponse()

# @login_required
# def stream(request, tag):
#     user = request.user
#     FollowingTagItem(user=user, query=tag).save()
#     return