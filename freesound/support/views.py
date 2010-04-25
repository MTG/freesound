from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template import RequestContext
from support.forms import ContactForm
from utils.mail import send_mail_template

def contact(request):
    email_sent = False
    user = None
    
    if request.user.is_authenticated():
        user = request.user 

    if request.POST:
        form = ContactForm(request, request.POST)
        if form.is_valid():
            subject = u"[support] " + form.cleaned_data['subject']
            email_from = form.cleaned_data['your_email']
            message = form.cleaned_data['message']

            # append some useful admin information to the email:
            if not user:
                try:
                    user = User.objects.get(email__iexact=email_from)
                except User.DoesNotExist: #@UndefinedVariable
                    pass
            
            send_mail_template(subject, "support/email_support.txt", locals(), email_from)

            email_sent = True
    else:
        if user:
            form = ContactForm(request, initial={"your_email": user.email})
        else:
            form = ContactForm(request)

    return render_to_response('support/contact.html', locals(), context_instance=RequestContext(request))