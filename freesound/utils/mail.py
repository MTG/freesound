from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail as core_send_mail
from django.template.loader import render_to_string

def send_mail(subject, email_body, email_from=None, email_to=[]):
    """ Sends email with a lot of defaults"""
    if not email_from:
        email_from = settings.DEFAULT_FROM_EMAIL
    
    if not email_to:
        email_to = [email for (name, email) in settings.ADMINS]
    elif not isinstance(email_to, tuple) or not isinstance(email_to, list):
        email_to = [email_to]
    
    try:
        core_send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, email_to, fail_silently=False)
    except:
        print "failed sending email"

def send_mail_template(subject, template, context, email_from=None, email_to=[]):
    context["current_site"] = Site.objects.get_current()
    context["settings"] = settings
    send_mail(subject, render_to_string(template, context), email_from, email_to)