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

from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template import RequestContext
from support.forms import ContactForm
from utils.mail import send_mail_template
from django.conf import settings

def contact(request):
    email_sent = False
    user = None
    
    if request.user.is_authenticated():
        user = request.user 

    if request.POST:
        form = ContactForm(request, request.POST)
        if form.is_valid():
            subject = u"[support] " + form.cleaned_data['subject']
            email_from = settings.DEFAULT_FROM_EMAIL
            message = form.cleaned_data['message']

            # append some useful admin information to the email:
            if not user:
                try:
                    user = User.objects.get(email__iexact=email_from)
                except User.DoesNotExist: #@UndefinedVariable
                    pass
            
            send_mail_template(subject, "support/email_support.txt", locals(), email_from, reply_to=form.cleaned_data['your_email'])

            email_sent = True
    else:
        if user:
            form = ContactForm(request, initial={"your_email": user.email})
        else:
            form = ContactForm(request)

    return render_to_response('support/contact.html', locals(), context_instance=RequestContext(request))