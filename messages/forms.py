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

from django import forms
from django.contrib.auth.models import User
from utils.forms import RecaptchaForm, HtmlCleaningCharField

class ManualUserField(forms.CharField):
    def clean(self, value):
        if not value:
            raise forms.ValidationError('Please enter a username.')
        try:
            return User.objects.get(username__iexact=value)
        except User.DoesNotExist: #@UndefinedVariable
            raise forms.ValidationError("We are sorry, but this username does not exist...")

def MessageReplyClassCreator(baseclass):
    class MessageReplyForm(baseclass):
        to = ManualUserField(widget=forms.TextInput(attrs={'size':'40'}))
        subject = forms.CharField(min_length=3, max_length=128, widget=forms.TextInput(attrs={'size':'80'}))
        body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))
    return MessageReplyForm

MessageReplyForm = MessageReplyClassCreator(RecaptchaForm)
MessageReplyFormNoCaptcha = MessageReplyClassCreator(forms.Form)