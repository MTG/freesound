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

from urllib2 import HTTPError, URLError

from akismet import Akismet, AkismetError
from django.conf import settings
from django.contrib.sites.models import Site

from general.models import AkismetSpam


def is_spam(request, comment):
    """Check if some text looks like spam"""

    # If request user has uploaded, moderated sounds, we don't check for spam
    if request.user.profile.is_trustworthy():
        return False

    # Hardcoded checks
    for spam_chunk in settings.SPAM_BLACKLIST:
        if spam_chunk in comment:
            return True

    # Akismet check
    domain = "https://%s" % Site.objects.get_current().domain
    api = Akismet(key=settings.AKISMET_KEY, blog_url=domain)
    data = {
        'user_ip': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'referrer': request.META.get('HTTP_REFERER', ''),
        'comment_type': 'comment',
        'comment_author': request.user.username.encode("utf-8") if request.user.is_authenticated else '',
    }
    if False: # set this to true to force a spam detection
        data['comment_author'] = "viagra-test-123"
    try:
        if api.comment_check(comment.encode('utf-8'), data=data, build_data=True):
            if request.user.is_authenticated:
                AkismetSpam.objects.create(user=request.user, spam=comment)
            return True
        else:
            return False
    except AkismetError: # failed to contact akismet...
        return False
    except HTTPError: # failed to contact akismet...
        return False
    except URLError: # failed to contact akismet...
        return False
