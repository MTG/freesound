from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from messages.forms import MessageReplyForm
from messages.models import Message, MessageBody
from utils.cache import invalidate_template_cache
from utils.functional import exceptional
from utils.mail import send_mail_template
from utils.pagination import paginate
from BeautifulSoup import BeautifulSoup
import json
from accounts.models import User
from django.http import HttpResponse

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
    return render_to_response('messages/inbox.html', paginate(request, qs), context_instance=RequestContext(request))


@login_required
def sent_messages(request):
    qs = base_qs.filter(user_from=request.user, is_archived=False, is_sent=True)
    return render_to_response('messages/sent.html', paginate(request, qs), context_instance=RequestContext(request))


@login_required
def archived_messages(request):
    qs = base_qs.filter(user_to=request.user, is_archived=True, is_sent=False)
    return render_to_response('messages/archived.html', paginate(request, qs), context_instance=RequestContext(request))


@login_required
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
        
    return render_to_response('messages/message.html', locals(), context_instance=RequestContext(request))

@login_required
def new_message(request, username=None, message_id=None):
    if request.method == 'POST':
        form = MessageReplyForm(request.POST)
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
                send_mail_template(u'you have a private message.', 'messages/email_new_message.txt', locals(), None, user_to.email)
            except:
                # if the email sending fails, ignore...
                pass
            
            return HttpResponseRedirect(reverse("messages"))
    else:
        form = MessageReplyForm()
        if message_id:
            try:
                message = Message.objects.get(id=message_id)

                if message.user_from != request.user and message.user_to != request.user:
                    raise Http404

                body = message.body.body.replace("\r\n", "\n").replace("\r", "\n")
                body = ''.join(BeautifulSoup(body).findAll(text=True))
                body = "\n".join([(">" if line.startswith(">") else "> ") + line.strip() for line in body.split("\n")])
                body = "> --- " + message.user_from.username + " wrote:\n>\n" + body
                
                subject = "re: " + message.subject
                to = message.user_from.username

                form = MessageReplyForm(initial=dict(to=to, subject=subject, body=body))
            except Message.DoesNotExist:
                pass
        elif username:
            form = MessageReplyForm(initial=dict(to=username))
    
    return render_to_response('messages/new.html', locals(), context_instance=RequestContext(request))

def username_lookup(request):
    results = []
    value = ""
    if request.method == "GET":
        if request.GET.has_key(u'q'):            
            value = request.GET[u'q']

            # When there is at least one character, start searching usernames (only among users previously contacted)
            if len(value) > 0:
                # Only autocompleting for previously contacted users 
                previously_contacted_user_ids = Message.objects.filter(user_from = request.user.id).values_list('user_to', flat='True').distinct()
                model_results = User.objects.filter(username__istartswith = value, id__in = previously_contacted_user_ids).order_by('username')#[0:30]
                index = 0
                for r in model_results:
                    results.append( (r.username,index) )
                    index = index + 1

    json_resp = json.dumps(results)
    return HttpResponse(json_resp, mimetype='application/json')

