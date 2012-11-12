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
from django.core.mail import send_mail as core_send_mail
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string

def send_mail(subject, email_body, email_from=None, email_to=[]):
    """ Sends email with a lot of defaults"""
    if not email_from:
        email_from = settings.DEFAULT_FROM_EMAIL
    
    if not email_to:
        email_to = [admin[1] for admin in settings.SUPPORT]
    elif not isinstance(email_to, tuple) and not isinstance(email_to, list):
        email_to = [email_to]

    if settings.ALLOWED_EMAILS:
        email_to = [email for email in email_to if email in settings.ALLOWED_EMAILS]

    try:
        #core_send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, email_to, fail_silently=False)
        emails = tuple(( (settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, [email]) for email in email_to ))
        send_mass_mail( emails, fail_silently = False)

        return True
    except:
        return False
    

def send_mail_template(subject, template, context, email_from=None, email_to=[]):
    context["settings"] = settings
    return send_mail(subject, render_to_string(template, context), email_from, email_to)
