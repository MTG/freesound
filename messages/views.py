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

from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.template import RequestContext
from messages.forms import MessageReplyForm, MessageReplyFormNoCaptcha
from messages.models import Message, MessageBody
from utils.cache import invalidate_template_cache
from utils.functional import exceptional
from utils.mail import send_mail_template
from utils.pagination import paginate
from BeautifulSoup import BeautifulSoup
import json
from textwrap import wrap
from accounts.models import User
from django.http import HttpResponse
from django.contrib import messages

@login_required
def messages_change_state(request):
    if request.method == "POST":
        choice = request.POST.get("choice", False)
        
        # get all ids, prefixed by "cb_" and after than an integer
        # only get the checkboxes that are "on"
        message_ids = filter(lambda x: x != None, [exceptional(int)(key.replace("cb_", "")) for key in request.POST.keys() if key.startswith("cb_") and request.POST.get(key) == "on"])

        if choice and message_ids:
            messages = Message.objects.filter(Q(user_to=request.user, is_sent=False) | Q(user_from=request.user, is_sent=True)).filter(id__in=message_ids)

            if choice == "a":
                messages.update(is_archived=True)
            elif choice == "d":
                messages.delete()
            elif choice == "r":
                messages.update(is_read=True)

            invalidate_template_cache("user_header", request.user.id)

    return HttpResponseRedirect(request.POST.get("next", reverse("messages")))

# base query object
base_qs = Message.objects.select_related('body', 'user_from', 'user_to')

@login_required
def inbox(request):
    qs = base_qs.filter(user_to=request.user, is_archived=False, is_sent=False)
    return render(request, 'messages/inbox.html', paginate(request, qs))


@login_required
def sent_messages(request):
    qs = base_qs.filter(user_from=request.user, is_archived=False, is_sent=True)
    return render(request, 'messages/sent.html', paginate(request, qs))


@login_required
def archived_messages(request):
    qs = base_qs.filter(user_to=request.user, is_archived=True, is_sent=False)
    return render(request, 'messages/archived.html', paginate(request, qs))


@login_required
@transaction.atomic()
def message(request, message_id):
    try:
        message = base_qs.get(id=message_id)
    except Message.DoesNotExist: #@UndefinedVariable
        raise Http404

    if message.user_from != request.user and message.user_to != request.user:
        raise Http404

    if not message.is_read:
        message.is_read = True
        invalidate_template_cache("user_header", request.user.id)
        message.save()

    return render(request, 'messages/message.html', locals())

@login_required
@transaction.atomic()
def new_message(request, username=None, message_id=None):
    
    if request.method == 'POST':

        if request.user.profile.num_sounds:
            form = MessageReplyFormNoCaptcha(request.POST)
        else:
            form = MessageReplyForm(request.POST)

        if request.user.profile.is_blocked_for_spam_reports():
            messages.add_message(request, messages.INFO, "You're not allowed to send the message because your account has been temporaly blocked after multiple spam reports")
        else:
            if form.is_valid():
                user_from = request.user
                user_to = form.cleaned_data["to"]
                subject = form.cleaned_data["subject"]
                body = MessageBody.objects.create(body=form.cleaned_data["body"])

                Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=True, is_archived=False, is_read=False)
                Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=False, is_archived=False, is_read=False)

                invalidate_template_cache("user_header", user_to.id)

                try:
                    # send the user an email to notify him of the sent message!
                    if user_to.profile.email_not_disabled("private_message"):
                        send_mail_template(u'you have a private message.', 'messages/email_new_message.txt', locals(),
                                           user_to=user_to)
                except:
                    # if the email sending fails, ignore...
                    pass

                return HttpResponseRedirect(reverse("messages"))
    else:
        if request.user.profile.num_sounds:
            form = MessageReplyFormNoCaptcha()
        else:
            form = MessageReplyForm()

        if message_id:
            try:
                message = Message.objects.get(id=message_id)

                if message.user_from != request.user and message.user_to != request.user:
                    raise Http404
                
                body = message.body.body.replace("\r\n", "\n").replace("\r", "\n")
                body = ''.join(BeautifulSoup(body).findAll(text=True))
                body = "\n".join([(">" if line.startswith(">") else "> ") + "\n> ".join(wrap(line.strip(),60)) for line in body.split("\n")])
                body = "> --- " + message.user_from.username + " wrote:\n>\n" + body

                subject = "re: " + message.subject
                to = message.user_from.username

                if request.user.profile.num_sounds:
                    form = MessageReplyFormNoCaptcha(initial=dict(to=to, subject=subject, body=body))
                else:
                    form = MessageReplyForm(initial=dict(to=to, subject=subject, body=body))
            except Message.DoesNotExist:
                pass
        elif username:
            if request.user.profile.num_sounds:
                form = MessageReplyFormNoCaptcha(initial=dict(to=username))
            else:
                form = MessageReplyForm(initial=dict(to=username))

    return render(request, 'messages/new.html', locals())

def username_lookup(request):
    results = []
    if request.method == "GET":
                # Only autocompleting for previously contacted users
                previously_contacted_user = list(Message.objects.filter(user_from = request.user.id)\
                        .values_list('user_to__username', flat='True').distinct())
                previously_contacted_user2 = list(Message.objects.filter(user_to = request.user.id)\
                        .values_list('user_from__username', flat='True').distinct())

                results = list(set(previously_contacted_user + previously_contacted_user2))
    json_resp = json.dumps(results)
    return HttpResponse(json_resp, content_type='application/json')

