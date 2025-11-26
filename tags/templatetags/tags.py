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

from django import template
from django.urls import reverse
from follow import follow_utils
from utils.tags import annotate_tags

register = template.Library()


@register.filter
def add_sizes(tags, arguments):
    sort, small_size, large_size = arguments.split(":")
    return annotate_tags(tags, sort, float(small_size), float(large_size))


@register.filter
def join_tags_exclude(list, exclude):
    return "/".join(sorted([x for x in list if x != exclude])) if list else None


@register.filter
def join_tags_include(list, include):
    return "/".join(sorted(list + [include])) if list else include


@register.inclusion_tag("molecules/bw_follow_tags_widget.html", takes_context=True)
def bw_follow_tags_widget(context):
    request = context["request"]
    slash_tag = "/".join(context["sqp"].get_tags_in_filters())
    follow_tags_url = ""
    unfollow_tags_url = ""
    show_unfollow_button = False
    if slash_tag:
        follow_tags_url = reverse("follow-tags", args=[slash_tag])
        unfollow_tags_url = reverse("unfollow-tags", args=[slash_tag])
        show_unfollow_button = False

        if request.user.is_authenticated:
            show_unfollow_button = follow_utils.is_user_following_tag(request.user, slash_tag)

    return {
        "follow_tags_url": follow_tags_url,
        "unfollow_tags_url": unfollow_tags_url,
        "show_unfollow_button": show_unfollow_button,
        "is_authenticated": request.user.is_authenticated,
    }
