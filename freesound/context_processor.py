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

import datetime

from django.conf import settings

from accounts.forms import BwFsAuthenticationForm, BwRegistrationForm, BwProblemsLoggingInForm
from messages.models import Message
from tickets.views import new_sound_tickets_count


def context_extra(request):
    # Get number of new messages, number of uploaded sounds pending moderation and number of sounds to moderate
    # variables so we can use them directly in base.html without a templatetag

    new_tickets_count = -1  # Initially set to -1 (to distinguish later users that can not moderate)
    num_pending_sounds = 0
    num_messages = 0
    spectrogram_preference = False

    if request.user.is_authenticated:
        if request.user.has_perm('tickets.can_moderate'):
            new_tickets_count = new_sound_tickets_count()
        num_pending_sounds = request.user.profile.num_sounds_pending_moderation()
        num_messages = Message.objects.filter(user_to=request.user, is_archived=False, is_sent=False, is_read=False).count()
        # TODO: the value before should be retrieved from Profile object once preference is stored there
        spectrogram_preference = request.session.get('preferSpectrogram', False)

    # Determine if anniversary special css and js content should be loaded
    # Animations will only be shown during the day of the anniversary
    # Special logo will be shown during 2 weeks after the anniversary
    load_anniversary_content = \
        datetime.datetime(2020, 4, 5, 0, 0) <= datetime.datetime.today() <= datetime.datetime(2020, 4, 20) or \
        request.GET.get('anniversary', '0') == '1'


    return {
        'media_url': settings.MEDIA_URL,
        'request': request,
        'last_restart_date': settings.LAST_RESTART_DATE,
        'new_tickets_count': new_tickets_count,
        'num_pending_sounds': num_pending_sounds,
        'num_messages': num_messages,
        'load_anniversary_content': load_anniversary_content,
        'next_path': request.GET.get('next', request.get_full_path()),  # Used for beast whoosh login modal only
        'login_form': BwFsAuthenticationForm(),  # Used for beast whoosh login modal only
        'registration_form': BwRegistrationForm(), # Used for beast whoosh login modal only
        'problems_logging_in_form': BwProblemsLoggingInForm(),  # Used for beast whoosh login modal only
        'spectrogram_preference': spectrogram_preference,
    }
