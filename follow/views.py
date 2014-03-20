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

from django.contrib.auth.decorators import login_required
from follow.models import FollowingUserItem
import accounts.views as accounts
from django.contrib.auth.models import User
from django.shortcuts import redirect

@login_required
def follow_user(request, username):
    # create following user item relation
    user_from = request.user
    user_to = User.objects.get(username=username)
    fui = FollowingUserItem(user_from=user_from, user_to=user_to)
    fui.save()
    # and then render the same page of the now followed user, with updated button information
    accounts.account(request, username)
    # TODO: is this ok?
    return redirect("/people/"+username)

@login_required
def unfollow_user(request, username):
    # get the following user item relation
    user_from = request.user
    user_to = User.objects.get(username=username)
    fui = FollowingUserItem.objects.get(user_from=user_from, user_to=user_to)
    # and delete it
    fui.delete()
    # and then render the same page of the now followed user, with updated button information
    accounts.account(request, username)
    # TODO: is this ok?
    return redirect("/people/"+username)