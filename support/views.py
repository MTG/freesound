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

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.shortcuts import render
from django.urls import reverse
from requests.exceptions import HTTPError
from zenpy import Zenpy
from zenpy.lib import api_objects as zendesk_api
from zenpy.lib.exception import APIException as ZendeskAPIException, ZenpyException

from comments.models import Comment
from support.forms import ContactForm
from utils.mail import send_mail_template_to_support

web_logger = logging.getLogger('web')


def create_zendesk_ticket(request_email, subject, message, user=None):
    if user is None:
        try:
            user = User.objects.get(email__iexact=request_email)
        except User.DoesNotExist:
            pass

    requester = zendesk_api.User(email=request_email)
    requester.name = 'Unknown username'
    custom_fields = []

    if user:
        is_active = user.is_active
        date_joined = user.date_joined
        last_login = user.last_login
        profile = user.profile
        num_sounds = profile.num_sounds
        num_posts = profile.num_posts
        num_comments = Comment.objects.filter(user=user).count()

        custom_fields = [
            zendesk_api.CustomField(id=30294425, value=is_active),
            zendesk_api.CustomField(id=30294725, value=date_joined),
            zendesk_api.CustomField(id=30153569, value=last_login),
            zendesk_api.CustomField(id=30295025, value=num_sounds),
            zendesk_api.CustomField(id=30295045, value=num_posts),
            zendesk_api.CustomField(id=30153729, value=num_comments),
        ]

        user_url = "https://%s%s" % (
            Site.objects.get_current().domain,
            reverse('account', args=[user.username])
        )

        message += "\n\n-- \n%s" % user_url

        requester.name = user.username

    return zendesk_api.Ticket(
        requester=requester,
        subject=subject,
        description=message,
        custom_fields=custom_fields
    )


def send_to_zendesk(request_email, subject, message, user=None):
    ticket = create_zendesk_ticket(request_email, subject, message, user)
    zenpy = Zenpy(
        email=settings.ZENDESK_EMAIL,
        token=settings.ZENDESK_TOKEN,
        subdomain='freesound'
    )
    try:
        zenpy.tickets.create(ticket)
    except (ZendeskAPIException, HTTPError, ZenpyException) as e:
        web_logger.info('Error creating Zendesk ticket: {}'.format(str(e)))


def send_email_to_support(request_email, subject, message, user=None):
    if user is None:
        try:
            user = User.objects.get(email__iexact=request_email)
        except User.DoesNotExist:
            pass

    send_mail_template_to_support(settings.EMAIL_SUBJECT_SUPPORT_EMAIL, "support/email_support.txt",
                                  {'message': message, 'user': user}, extra_subject=subject, reply_to=request_email)


def contact(request):
    request_sent = False
    user = None

    if request.user.is_authenticated:
        user = request.user

    if request.POST:
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            if getattr(settings, 'USE_ZENDESK_FOR_SUPPORT_REQUESTS', False):
                send_to_zendesk(form.cleaned_data['your_email'], subject, message)
            else:
                send_email_to_support(form.cleaned_data['your_email'], subject, message)
            request_sent = True
    else:
        if user:
            form = ContactForm(initial={"your_email": user.profile.get_email_for_delivery()})
        else:
            form = ContactForm()
    tvars = {'form': form, 'request_sent': request_sent}
    return render(request, 'support/contact.html', tvars)
