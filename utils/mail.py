from django.conf import settings
from django.core.mail import send_mail as core_send_mail
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string

def send_mail(subject, email_body, email_from=None, email_to=[]):
    """ Sends email with a lot of defaults"""
    if not email_from:
        email_from = settings.DEFAULT_FROM_EMAIL
    
    if not email_to:
        email_to = [admin[1] for admin in settings.SUPPORT]
    elif not isinstance(email_to, tuple) and not isinstance(email_to, list):
        email_to = [email_to]

    try:
        #core_send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, email_to, fail_silently=False)
        emails = tuple(( (settings.EMAIL_SUBJECT_PREFIX + subject, email_body, email_from, [email]) for email in email_to ))
        send_mass_mail( emails, fail_silently = False)

        return True
    except:
        return False
    

def send_mail_template(subject, template, context, email_from=None, email_to=[]):
    context["settings"] = settings
    return send_mail(subject, render_to_string(template, context), email_from, email_to)
