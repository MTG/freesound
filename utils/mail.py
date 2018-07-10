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
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from django.core.mail import get_connection
from django.core.exceptions import ObjectDoesNotExist


def transform_unique_email(email):
    """
    To avoid duplicated emails, in migration accounts.0009_sameuser we automatically change existing
    duplicated user emails by the contents returned in this function. This is reused for further
    checks in utils.mail.replace_email_to and accounts.views.multi_email_cleanup. 
    """
    return "dupemail+%s@freesound.org" % (email.replace("@", "%"), )


def _ensure_list(item):
    if not isinstance(item, tuple) and not isinstance(item, list):
        return [item]
    return item


def send_mail(subject, email_body, user_to=None, email_to=None, email_from=None, reply_to=None):
    """
    Sends email with a lot of defaults. The function will check if user's email is valid based on bounce info and will
    not send to this user in other case. Parameters user_to and email_to are mutually exclusive, if one is set, other
    should be None.
    @:param user_to is a single user object, or a list of them. If it is set, email_to parameter should be None
    @:param email_to is a single email string, or a list of them. If it is set, user_to parameter should be None.
    Strings should be only used for emails that are not related to users, e.g. support or admins, otherwise user_to
    parameter should be used to provide user object(s) instead of email address
    @:param email_from is a email string that shows up as sender. The default value is DEFAULT_FROM_EMAIL in config
    @:param reply_to can only be a single email address that will be added as a header to all mails being sent
    @:returns False if no emails were send successfully, True otherwise
    """
    assert bool(user_to) != bool(email_to), "One of parameters user_to and email_to should be set, but not both"

    if email_from is None:
        email_from = settings.DEFAULT_FROM_EMAIL

    if user_to:
        user_to = _ensure_list(user_to)
        email_to = []
        for user in user_to:

            # check if user's email is valid for delivery and add the correct email address to the list og email_to
            if user.profile.email_is_valid():
                email_to.append(user.profile.get_email_for_delivery())

            if len(email_to) == 0:  # all users have invalid emails
                return False

    if email_to:
        email_to = _ensure_list(email_to)

    if settings.ALLOWED_EMAILS:  # for testing purposes, so we don't accidentally send emails to users
        email_to = [email for email in email_to if email in settings.ALLOWED_EMAILS]

    try:
        emails = tuple(((settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, [email])
                        for email in email_to))

        # Replicating send_mass_mail functionality and adding reply-to header if requires
        connection = get_connection(username=None, password=None, fail_silently=False)
        headers = None
        if reply_to:
            headers = {'Reply-To': reply_to}
        messages = [EmailMessage(subject, message, sender, recipient, headers=headers)
                    for subject, message, sender, recipient in emails]

        connection.send_messages(messages)
        return True

    except Exception:
        return False


def send_mail_template(subject, template, context, user_to=None, email_to=None, email_from=None, reply_to=None):
    context["settings"] = settings
    return send_mail(subject, render_to_string(template, context), user_to, email_to, email_from, reply_to)


def send_mail_template_to_support(subject, template, context, email_from=None, reply_to=None):
    email_to = []
    for email in settings.SUPPORT:
        email_to.append(email[1])
    return send_mail_template(subject, template, context, email_to=email_to, email_from=email_from, reply_to=reply_to)


def render_mail_template(template, context):
    context["settings"] = settings
    return render_to_string(template, context)
