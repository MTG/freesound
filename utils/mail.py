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


def transform_unique_email(email):
    """
    To avoid duplicated emails, in migration accounts.0009_sameuser we automatically change existing
    duplicated user emails by the contents returned in this function. This is reused for further
    checks in utils.mail.replace_email_to and accounts.views.multi_email_cleanup. 
    """
    return "dupemail+%s@freesound.org" % (email.replace("@", "%"), )


def replace_email_to(func):
    """
    This decorator checks the email_to list and replaces any addresses that need replacement
    according to the SameUser table (see https://github.com/MTG/freesound/pull/763). In our process
    of removing dublicated email addresses from our users table we set up a temporary table to
    store the original email addresses of users whose email was automatically changed to prevent 
    duplicates. In this function we make sure that emails are sent to the original address and not
    the one we edited to prevent duplicates. 
    At some point in time, SameUser table should become empty (when users update their addresses) and
    then we'll be able to remove this decorator.
    """
    def wrapper(subject, email_body, email_from=None, email_to=list(), reply_to=None):

        # Process email_to like we do in normal 'send_mail'
        if not email_to:
            if email_to == '':
                return True
            email_to = [admin[1] for admin in settings.SUPPORT]
        elif not isinstance(email_to, tuple) and not isinstance(email_to, list):
            email_to = [email_to]

        from accounts.models import SameUser
        emails_mapping = {su.secondary_trans_email: su.orig_email for su in SameUser.objects.all()}
        email_to = list(set([emails_mapping.get(email, email) for email in email_to]))
        return func(subject, email_body, email_from, email_to, reply_to)
    return wrapper


@replace_email_to
def send_mail(subject, email_body, email_from=None, email_to=list(), reply_to=None):
    """
    Sends email with a lot of defaults
    @:param email_to can be either string, or user object, or a list of those. If it is a user object, the function will
    check if email is valid based on bounce info 
    @:param reply_to parameter can only be a single email address that will be added as a header
    to all mails being sent.
    @:returns False if an exception occurred during email sending procedure, or if there are users with valid emails in 
    email_to parameter; True otherwise
    """
    if not email_from:
        email_from = settings.DEFAULT_FROM_EMAIL

    if not email_to:
        # If email_to is empty, don't send email, otherwise (email_to 'False' but not '',
        # send to default support emails)
        if email_to == '':
            return True
        email_to = [admin[1] for admin in settings.SUPPORT]
    elif not isinstance(email_to, tuple) and not isinstance(email_to, list):
        email_to = [email_to]

    email_list = []
    for item in email_to:
        try:  # assume it is a User object
            if item.profile.email_is_valid():
                email_list.append(item.email)
        except AttributeError:  # probably explicit string
            email_list.append(item)

    if len(email_list) == 0:
        return False

    if settings.ALLOWED_EMAILS:
        email_list = [email for email in email_list if email in settings.ALLOWED_EMAILS]

    try:
        emails = tuple(
            ((settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, [email]) for email in email_list)
        )

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


def send_mail_template(subject, template, context, email_from=None, email_to=list(), reply_to=None):
    context["settings"] = settings
    return send_mail(subject, render_to_string(template, context), email_from, email_to, reply_to=reply_to)


def render_mail_template(template, context):
    context["settings"] = settings
    return render_to_string(template, context)
