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

from django.conf import settings
from tickets.views import new_sound_tickets_count
from messages.models import Message


def context_extra(request):
    # Get number of new messages, number of uploaded sounds pending moderation and number of sounds to moderate
    # variables so we can use them directly in base.html without a templatetag

    new_tickets_count = -1  # Initially set to -1 (to distinguish later users that can not moderate)
    num_pending_sounds = 0
    num_messages = 0

    if request.user.is_authenticated:
        if request.user.has_perm('tickets.can_moderate'):
            new_tickets_count = new_sound_tickets_count()
        num_pending_sounds = request.user.profile.num_sounds_pending_moderation()
        num_messages = Message.objects.filter(user_to=request.user, is_archived=False, is_sent=False, is_read=False).count()

    return {
        'use_js_dev_server': settings.USE_JS_DEVELOPMENT_SERVER,
        'media_url': settings.MEDIA_URL,
        'request': request,
        'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
        'last_restart_date': settings.LAST_RESTART_DATE,
        'new_tickets_count': new_tickets_count,
        'num_pending_sounds': num_pending_sounds,
        'num_messages': num_messages,
    }
