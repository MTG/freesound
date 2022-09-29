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

import json
from textwrap import wrap

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse

from messages.forms import MessageReplyForm, MessageReplyFormWithCaptcha, BwMessageReplyForm, BwMessageReplyFormWithCaptcha
from messages.models import Message, MessageBody
from utils.cache import invalidate_user_template_caches
from utils.frontend_handling import render, using_beastwhoosh
from utils.mail import send_mail_template
from utils.pagination import paginate


@login_required
def messages_change_state(request):
    if request.method == "POST":
        choice = request.POST.get("choice", False)

        if not using_beastwhoosh(request):
            # get all message ids in the format `cb_[number]` which have a value of 'on'
            message_ids = []
            for key, val in request.POST.items():
                if key.startswith('cb_') and val == 'on':
                    try:
                        msgid = int(key.replace('cb_', ''))
                        message_ids.append(msgid)
                    except ValueError:
                        pass
        else:
            # If using beastwhoosh, the IDs will come in a different form field
            message_ids = [int(mid) for mid in request.POST.get("ids", "").split(',')]

        if choice and message_ids:
            fs_messages = Message.objects.filter(Q(user_to=request.user, is_sent=False) |
                                              Q(user_from=request.user, is_sent=True)).filter(id__in=message_ids)

            if choice == "a":
                if using_beastwhoosh(request):
                    for message in fs_messages:
                        # In BW we allow the option to toggle archived/unarchived, so we need to iterate messages
                        # one by one
                        message.is_archived = not message.is_archived
                        message.save()
                else:
                    fs_messages.update(is_archived=True)
            elif choice == "d":
                fs_messages.delete()
            elif choice == "r":
                if using_beastwhoosh(request):
                    for message in fs_messages:
                        # In BW we allow the option to toggle read/unread, so we need to iterate messages one by one
                        message.is_read = not message.is_read
                        message.save()
                else:
                    fs_messages.update(is_read=True)

            invalidate_user_template_caches(request.user.id)

    return HttpResponseRedirect(request.POST.get("next", reverse("messages")))


# base query object
base_qs = Message.objects.select_related('body', 'user_from', 'user_to')


@login_required
def inbox(request):
    qs = base_qs.filter(user_to=request.user, is_archived=False, is_sent=False)
    tvars = {'list_type': 'inbox'}  # Used in BW tabs nav only
    tvars.update(paginate(
        request, qs,
        items_per_page=settings.MESSAGES_PER_PAGE_BW if using_beastwhoosh(request) else settings.MESSAGES_PER_PAGE))
    return render(request, 'messages/inbox.html', tvars)


@login_required
def sent_messages(request):
    qs = base_qs.filter(user_from=request.user, is_archived=False, is_sent=True)
    tvars = {
        'list_type': 'sent',  # Used in BW tabs nav only
        'hide_toggle_read_unread': True,   # Used to control available actions in BW only
        'hide_archive_unarchive': True   # Used to control available actions in BW only
    } 
    tvars.update(paginate(
        request, qs,
        items_per_page=settings.MESSAGES_PER_PAGE_BW if using_beastwhoosh(request) else settings.MESSAGES_PER_PAGE))
    return render(request, 'messages/sent.html', tvars)


@login_required
def archived_messages(request):
    qs = base_qs.filter(user_to=request.user, is_archived=True, is_sent=False)
    tvars = {'list_type': 'archived'}  # Used in BW tabs nav only
    tvars.update(paginate(
        request, qs,
        items_per_page=settings.MESSAGES_PER_PAGE_BW if using_beastwhoosh(request) else settings.MESSAGES_PER_PAGE))
    return render(request, 'messages/archived.html', tvars)


@login_required
@transaction.atomic()
def message(request, message_id):
    try:
        message = base_qs.get(id=message_id)
    except Message.DoesNotExist:
        raise Http404

    if message.user_from != request.user and message.user_to != request.user:
        raise Http404

    if not message.is_read:
        message.is_read = True
        invalidate_user_template_caches(request.user.id)
        message.save()

    tvars = {'message': message}
    return render(request, 'messages/message.html', tvars)


@login_required
@transaction.atomic()
def new_message(request, username=None, message_id=None):

    if request.user.profile.is_trustworthy():
        form_class = BwMessageReplyForm if using_beastwhoosh(request) else MessageReplyForm
    else:
        form_class = BwMessageReplyFormWithCaptcha if using_beastwhoosh(request) else MessageReplyFormWithCaptcha
    
    if request.method == 'POST':
        form = form_class(request, request.POST)

        if request.user.profile.is_blocked_for_spam_reports():
            messages.add_message(request, messages.INFO, "You're not allowed to send the message because your account "
                                                         "has been temporally blocked after multiple spam reports")
        else:
            if form.is_valid():
                user_from = request.user
                user_to = form.cleaned_data["to"]
                subject = form.cleaned_data["subject"]
                body = MessageBody.objects.create(body=form.cleaned_data["body"])

                Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=True,
                                       is_archived=False, is_read=False)
                Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=False,
                                       is_archived=False, is_read=False)

                invalidate_user_template_caches(user_to.id)

                try:
                    # send the user an email to notify him of the sent message!
                    tvars = {'user_to': user_to,
                             'user_from': user_from}

                    send_mail_template(settings.EMAIL_SUBJECT_PRIVATE_MESSAGE, 'messages/email_new_message.txt', tvars,
                                       user_to=user_to, email_type_preference_check="private_message")
                except:
                    # if the email sending fails, ignore...
                    pass

                return HttpResponseRedirect(reverse("messages"))
    else:
        if message_id:
            try:
                message = Message.objects.get(id=message_id)

                if message.user_from != request.user and message.user_to != request.user:
                    raise Http404
                
                body = message.body.body.replace("\r\n", "\n").replace("\r", "\n")
                body = quote_message_for_reply(body, message.user_from.username)

                subject = "re: " + message.subject
                to = message.user_from.username

                form = form_class(request, initial={"to": to, "subject": subject, "body": body})
            except Message.DoesNotExist:
                pass
        elif username:
            form = form_class(request, initial={"to": username})
        else:
            form = form_class(request)

    tvars = {'form': form}
    return render(request, 'messages/new.html', tvars)


def quote_message_for_reply(body, username):
    body = ''.join(BeautifulSoup(body).find_all(text=True))
    body = "\n".join([(">" if line.startswith(">") else "> ") + "\n> ".join(wrap(line.strip(), 60))
                        for line in body.split("\n")])
    body = "> --- " + username + " wrote:\n>\n" + body
    return body


def get_previously_contacted_usernames(user):
    # Get a list of previously contacted usernames (in no particular order)
    usernames = list(Message.objects.select_related('user_from', 'user_to')
                     .filter(Q(user_from=user) | Q(user_to=user))
                     .values_list('user_to__username', 'user_from__username'))
    return list(set([item for sublist in usernames for item in sublist]))


@login_required
def username_lookup(request):
    results = []
    if request.method == "GET":
        results = get_previously_contacted_usernames(request.user)
    if using_beastwhoosh(request):
        # NOTE: key needs to be "suggestions" below so the autocomplete JS part of the code works properly
        return JsonResponse({'suggestions': results})
    else:
        json_resp = json.dumps(results)
        return HttpResponse(json_resp, content_type='application/json')
