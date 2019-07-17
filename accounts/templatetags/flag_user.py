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
def flag_user(context, flag_type, item, content_user):
    show = True
    link_text = "Report spam/offensive"

    if hasattr(item, 'num_flags'):
        flagged = item.num_flags > 0
    else:
        # TODO: Bug here that only checks the object id and not the content type id
        flagged = UserFlag.objects.filter(user=content_user,
                                          reporting_user=context['request'].user,
                                          object_id=item.id).exists()

    if not context['request'].user.is_authenticated:
        show = False

    show = show and content_user.profile.is_trustworthy()

    return {
            'done_text': "Marked as spam/offensive",
            'flagged': flagged,
            'flag_type': flag_type,
            'username': content_user.username,
            'content_obj_id': item.id,
            'media_url': context['media_url'],
            'link_text': link_text,
            'show': show}
