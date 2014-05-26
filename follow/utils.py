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

def get_users_following(user):
    items = FollowingUserItem.objects.filter(user_from=user)
    return [item.user_to for item in items]

def get_users_followers(user):
    items = FollowingUserItem.objects.filter(user_to=user)
    return [item.user_from for item in items]

def get_tags_following(user):
    items = FollowingQueryItem.objects.filter(user=user)
    return [item.query for item in items]
