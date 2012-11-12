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
from sounds.models import Sound
from comments.models import Comment
from forum.models import Post

register = template.Library()

@register.inclusion_tag("accounts/active_user_content.html", takes_context=True)
def active_user_content(context,user_obj, content_type):
    content = None
    if content_type == "sound":
        content = Sound.public.select_related().filter(user=user_obj).order_by("-created")[0]
    elif  content_type == "post":
        content = Post.objects.select_related().filter(author=user_obj).order_by("-created")[0]
    elif content_type == "comment":
        content = Comment.objects.select_related().filter(user=user_obj).order_by("-created")[0]
    return {'content_type':content_type,'content':content,'user':user_obj,'media_url': context['media_url']}
