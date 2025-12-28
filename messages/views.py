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
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from messages.forms import MessageReplyForm, MessageReplyFormWithCaptcha
from messages.models import Message, MessageBody
from utils.cache import invalidate_user_template_caches
from utils.mail import send_mail_template
from utils.pagination import paginate


@login_required
def messages_change_state(request):
    if request.method == "POST":
        choice = request.POST.get("choice", False)
        message_ids = [int(mid) for mid in request.POST.get("ids", "").split(",")]
        if choice and message_ids:
            fs_messages = Message.objects.filter(
                Q(user_to=request.user, is_sent=False) | Q(user_from=request.user, is_sent=True)
            ).filter(id__in=message_ids)
            if choice == "a":
                for message in fs_messages:
                    message.is_archived = not message.is_archived
                    message.save()
            elif choice == "d":
                fs_messages.delete()
            elif choice == "r":
                for message in fs_messages:
                    message.is_read = not message.is_read
                    message.save()
            invalidate_user_template_caches(request.user.id)
    return HttpResponseRedirect(request.POST.get("next", reverse("messages")))


# base query object
base_qs = Message.objects.select_related("body", "user_from", "user_from__profile", "user_to", "user_to__profile")


@login_required
def inbox(request):
    qs = base_qs.filter(user_to=request.user, is_archived=False, is_sent=False)
    tvars = {"list_type": "inbox"}
    tvars.update(paginate(request, qs, items_per_page=settings.MESSAGES_PER_PAGE))
    return render(request, "messages/inbox.html", tvars)


@login_required
def sent_messages(request):
    qs = base_qs.filter(user_from=request.user, is_archived=False, is_sent=True)
    tvars = {"list_type": "sent", "hide_toggle_read_unread": True, "hide_archive_unarchive": True}
    tvars.update(paginate(request, qs, items_per_page=settings.MESSAGES_PER_PAGE))
    return render(request, "messages/sent.html", tvars)


@login_required
def archived_messages(request):
    qs = base_qs.filter(user_to=request.user, is_archived=True, is_sent=False)
    tvars = {"list_type": "archived"}
    tvars.update(paginate(request, qs, items_per_page=settings.MESSAGES_PER_PAGE))
    return render(request, "messages/archived.html", tvars)


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

    tvars = {"message": message}
    return render(request, "messages/message.html", tvars)


@login_required
@transaction.atomic()
def new_message(request, username=None, message_id=None):
    is_reply = bool(message_id)
    if request.user.profile.is_trustworthy():
        form_class = MessageReplyForm
    else:
        form_class = MessageReplyFormWithCaptcha

    if request.method == "POST":
        form = form_class(request, request.POST)

        if request.user.profile.is_blocked_for_spam_reports():
            messages.add_message(
                request,
                messages.INFO,
                "You're not allowed to send the message because your account "
                "has been temporally blocked after multiple spam reports",
            )
        else:
            if form.is_valid():
                user_from = request.user
                user_to = form.cleaned_data["to"]
                subject = form.cleaned_data["subject"]
                body = MessageBody.objects.create(body=form.cleaned_data["body"])

                Message.objects.create(
                    user_from=user_from,
                    user_to=user_to,
                    subject=subject,
                    body=body,
                    is_sent=True,
                    is_archived=False,
                    is_read=False,
                )
                Message.objects.create(
                    user_from=user_from,
                    user_to=user_to,
                    subject=subject,
                    body=body,
                    is_sent=False,
                    is_archived=False,
                    is_read=False,
                )

                invalidate_user_template_caches(user_to.id)

                try:
                    # send the user an email to notify him of the sent message!
                    tvars = {"user_to": user_to, "user_from": user_from}
                    send_mail_template(
                        settings.EMAIL_SUBJECT_PRIVATE_MESSAGE,
                        "emails/email_new_message.txt",
                        tvars,
                        user_to=user_to,
                        email_type_preference_check="private_message",
                    )
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
                elif message.user_from == request.user:
                    to = message.user_to.username
                else:
                    to = message.user_from.username

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

    tvars = {"form": form, "is_reply": is_reply}
    return render(request, "messages/new.html", tvars)


def quote_message_for_reply(body, username):
    body = "".join(BeautifulSoup(body, "html.parser").find_all(string=True))
    body = "\n".join(
        [(">" if line.startswith(">") else "> ") + "\n> ".join(wrap(line.strip(), 60)) for line in body.split("\n")]
    )
    body = "> --- " + username + " wrote:\n>\n" + body
    return body


def get_previously_contacted_usernames(user):
    # Get a list of previously contacted usernames (in no particular order)
    usernames = list(
        Message.objects.select_related("user_from", "user_to")
        .filter(Q(user_from=user) | Q(user_to=user))
        .values_list("user_to__username", "user_from__username")
    )
    return list({item for sublist in usernames for item in sublist})


@login_required
def username_lookup(request):
    results = []
    if request.method == "GET":
        query = request.GET.get("q", None)
        if query is not None and query.strip():
            results = get_previously_contacted_usernames(request.user)
            results = [result for result in results if query in result]
    json_resp = json.dumps(results)
    return HttpResponse(json_resp, content_type="application/json")
