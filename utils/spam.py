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

from urllib.error import HTTPError, URLError

from akismet import Akismet, AkismetError, APIKeyError, ConfigurationError
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

    if settings.AKISMET_KEY:
        # Akismet check
        domain = f"https://{Site.objects.get_current().domain}"
        try:
            api = Akismet(key=settings.AKISMET_KEY, blog_url=domain)
        except (APIKeyError, ConfigurationError):
            return False

        try:
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                user_ip = x_forwarded_for.split(",")[0].strip()
            else:
                user_ip = "127.0.0.1"
            if api.comment_check(
                user_ip=user_ip,
                user_agent=request.headers.get("user-agent", None),
                referrer=request.headers.get("referer", None),
                comment_type="comment",
                comment_author=request.user.username.encode("utf-8") if request.user.is_authenticated else None,
                comment_content=comment.encode("utf-8"),
            ):
                if request.user.is_authenticated:
                    AkismetSpam.objects.create(user=request.user, spam=comment)
                return True
            else:
                return False
        except (AkismetError, HTTPError, URLError):  # failed to contact akismet...
            return False
