import json
import base64
from django import forms
from django.utils.safestring import mark_safe

from models import DonationCampaign

class DonateForm(forms.Form):
    RADIO_CHOICES = []

    donation_type = forms.ChoiceField(widget=forms.RadioSelect(), choices=RADIO_CHOICES)
    name_option = forms.CharField(required=False, max_length=255)
    amount = forms.FloatField(initial=10.0, min_value=0.5)
    recurring = forms.BooleanField(required=False, initial=False,
            label='I want this to be a recurring monthly donation',)
    show_amount = forms.BooleanField(
            label='Make donated amount public',
            required=False,
            initial=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        default_donation_amount = kwargs.pop('default_donation_amount', None)
        super(DonateForm, self).__init__(*args, **kwargs)
        choices = [
            ('1', "Anonymous"),
            ('2', "Other... "),
        ]
        self.user_id = None
        if user.username:
            self.user_id = user.id
            choices.insert(0, ('0', user.username))
            self.initial['donation_type'] = '0'
        else:
            self.initial['donation_type'] = '1'

        self.fields['donation_type'].choices = choices

        if default_donation_amount is not None:
            self.initial['amount'] = float(default_donation_amount)

    def clean(self):
        cleaned_data = super(DonateForm, self).clean()
        amount = cleaned_data.get('amount')
        try:
            if not amount or float(amount) < 1:
                raise forms.ValidationError('The amount must be more than 1')
        except ValueError:
            raise forms.ValidationError('The amount must be a valid number, use \'.\' for decimals')

        campaign = DonationCampaign.objects.order_by('date_start').last()
        returned_data = {
                "campaign_id": campaign.id,
                "display_amount": cleaned_data.get('show_amount')
                }

        annon = cleaned_data.get('donation_type')

        # We store the user even if the donation is annonymous
        if self.user_id :
            returned_data['user_id'] = self.user_id

        if annon == '1':
            returned_data['name'] = "Anonymous"
        elif annon == '2':
            returned_data['name'] = cleaned_data.get('name_option', '')
            if returned_data['name'] == '':
                raise forms.ValidationError('You have to enter a name to display')


        # Paypal gives only one field to add extra data so we send it as b64
        self.encoded_data = base64.b64encode(json.dumps(returned_data))
        return cleaned_data


class BwDonateForm(DonateForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super(BwDonateForm, self).__init__(*args, **kwargs)

        self.fields['donation_type'].label = \
            mark_safe('Please choose the <b>name</b> that will appear with the donation:')
        self.fields['donation_type'].widget.attrs['class'] = 'bw-radio'
        self.fields['name_option'].label = False
        self.fields['name_option'].widget.attrs['class'] = 'display-none'
        self.fields['name_option'].widget.attrs['placeholder'] = 'Write the name here'
        self.fields['amount'].label = mark_safe('Donation amount (&euro;):')
        self.fields['amount'].widget.attrs['class'] = 'v-spacing-top-1'
        self.fields['recurring'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['show_amount'].widget.attrs['class'] = 'bw-checkbox'
