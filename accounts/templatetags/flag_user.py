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
from accounts.models import UserFlag
register = template.Library()


@register.inclusion_tag("accounts/flag_user.html", takes_context=True)
def flag_user(context, flag_type, username, content_id, text = None, user_sounds = None):

    no_show = False
    link_text = "Report spam/offensive"

    if not context['request'].user.is_authenticated:
        no_show = True
        flagged = False
    else:
        flagged = UserFlag.objects.filter(
            user__username=username, reporting_user=context['request'].user, object_id=content_id
        ).exists()
        if text:
            link_text = text

    return {'user_sounds': user_sounds,
            'done_text': "Marked as spam/offensive",  # Not used in BW
            'flagged': flagged,
            'flag_type': flag_type,
            'username': username,
            'content_obj_id': content_id,
            'link_text': link_text,
            'no_show': no_show}
