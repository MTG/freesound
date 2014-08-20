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
from django.core.mail.message import EmailMessage
from django.core.mail import send_mass_mail, get_connection
from django.template.loader import render_to_string
from django.core.mail import get_connection, EmailMultiAlternatives

def send_mail(subject, email_body, email_from=None, email_to=list(), reply_to=None):
    """
    Sends email with a lot of defaults
    'reply_to' parameter can only be a single email address that will be added as a header
    to all mails being sent.
    """
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

        # Replicating send_mass_mail functionality and adding reply-to header if requires
        connection = get_connection(username=None,
                                    password=None,
                                    fail_silently=False)
        headers = None
        if reply_to:
            headers = {'Reply-To': reply_to}
        messages = [EmailMessage(subject, message, sender, recipient, headers=headers)
                    for subject, message, sender, recipient in emails]

        connection.send_messages(messages)

        return True
    except:
        return False


def send_mail_template(subject, template, context, email_from=None, email_to=[], reply_to=None):
    context["settings"] = settings
    return send_mail(subject, render_to_string(template, context), email_from, email_to)


def render_mail_template(template, context):
    context["settings"] = settings
    return render_to_string(template, context)


def send_mass_html_mail(datatuple, fail_silently=False, user=None, password=None, connection=None):
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    """
    connection = connection or get_connection(
        username=user, password=password, fail_silently=fail_silently
    )

    messages = []
    for subject, text, html, from_email, recipient in datatuple:
        message = EmailMultiAlternatives(subject, text, from_email, recipient)
        message.attach_alternative(html, 'text/html')
        messages.append(message)

    return connection.send_messages(messages)
