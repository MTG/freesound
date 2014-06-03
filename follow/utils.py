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