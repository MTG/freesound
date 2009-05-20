from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from forms import *
from models import *
from utils.functional import exceptional
from utils.mail import send_mail_template

def combine_dicts(dict1, dict2):
    return dict(dict1.items() + dict2.items())

def paginate(request, qs):
    paginator = Paginator(qs, 20)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1
    
    return dict(paginator=paginator, current_page=current_page, page=page)

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
    except Message.DoesNotExist:
        raise Http404
    
    if message.user_from != request.user and message.user_to != request.user:
        raise Http404
    
    if not message.is_read:
        message.is_read = True
        message.save()
        
    return render_to_response('messages/message.html', locals(), context_instance=RequestContext(request))

@login_required
def new_message(request, username=None):
    if request.method == 'POST':
        form = PostReplyForm(request.POST)
        if form.is_valid():
            user_from = request.user
            user_to = form.cleaned_data["to"]
            subject = form.cleaned_data["subject"]
            body = MessageBody.objects.create(body=form.cleaned_data["body"])

            Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=True, is_archived=False, is_read=False)
            Message.objects.create(user_from=user_from, user_to=user_to, subject=subject, body=body, is_sent=False, is_archived=False, is_read=False)
            
            # send the user an email to notify him of the sent message!
            send_mail_template(u'You have a private message.', 'messages/email_new_message.txt', locals(), None, user_to.email)
            
            return HttpResponseRedirect(reverse("messages"))
    else:
        if username:
            form = PostReplyForm(initial=dict(to=username))
        else:
            form = PostReplyForm()
    
    return render_to_response('messages/new.html', locals(), context_instance=RequestContext(request))