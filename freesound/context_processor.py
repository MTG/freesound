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

from accounts.forms import BwFsAuthenticationForm, BwProblemsLoggingInForm
from forum.models import Post
from messages.models import Message
from tickets.views import new_sound_tickets_count


def context_extra(request):
    # Add extra "global" context that we can use in templates
    tvars = {
        'request': request,
    }
    
    # Determine if extra context needs to be computed (this will allways be true expect for most of api calls and embeds)
    # There'll be other places in which the extra context is not needed, but this will serve as an approximation
    should_compute_extra_context = True    
    if request.path.startswith('/apiv2/') and \
        'apply' not in request.path and \
        'login' not in request.path and \
        'logout' not in request.path:
        should_compute_extra_context = False
    if request.path.startswith('/embed/'):
        should_compute_extra_context = False

    if should_compute_extra_context:
        new_tickets_count = -1  # Initially set to -1 (to distinguish later users that can not moderate)
        num_pending_sounds = 0
        num_messages = 0
        new_posts_pending_moderation = 0

        if request.user.is_authenticated:
            if request.user.has_perm('tickets.can_moderate'):
                new_tickets_count = new_sound_tickets_count()
            if request.user.has_perm('forum.can_moderate_forum'):
                new_posts_pending_moderation = Post.objects.filter(moderation_state='NM').count()
            num_pending_sounds = request.user.profile.num_sounds_pending_moderation()
            num_messages = Message.objects.filter(user_to=request.user, is_archived=False, is_sent=False, is_read=False).count()

        # Determine if anniversary special css and js content should be loaded
        # Animations will only be shown during the day of the anniversary
        # Special logo will be shown during 2 weeks after the anniversary
        load_anniversary_content = \
            datetime.datetime(2020, 4, 5, 0, 0) <= datetime.datetime.today() <= datetime.datetime(2020, 4, 20) or \
            request.GET.get('anniversary', '0') == '1'

        tvars.update({
            'last_restart_date': settings.LAST_RESTART_DATE,
            'new_tickets_count': new_tickets_count,
            'new_posts_pending_moderation': new_posts_pending_moderation,
            'num_pending_sounds': num_pending_sounds,
            'num_messages': num_messages,
            'load_anniversary_content': load_anniversary_content,
            'next_path': request.GET.get('next', request.get_full_path()),
            'login_form': BwFsAuthenticationForm(),
            'problems_logging_in_form': BwProblemsLoggingInForm(),
            'system_prefers_dark_theme': request.COOKIES.get('systemPrefersDarkTheme', 'no') == 'yes'  # Determine the user's system preference for dark/light theme (for non authenticated users, always use light theme)
        })
    
    return tvars
