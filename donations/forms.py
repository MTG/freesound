import json
import base64
from django import forms
from models import DonationCampaign

class DonateForm(forms.Form):
    RADIO_CHOICES = []

    donation_type = forms.ChoiceField(widget=forms.RadioSelect(), choices=RADIO_CHOICES)
    name_option = forms.CharField(required=False)
    amount = forms.CharField(required=True, initial="5")
    recurring = forms.BooleanField(required=False, initial=False,
            label='I want this to be a recurring monthly donation',)
    show_amount = forms.BooleanField(
            label='Make donated amount public',
            required=False,
            initial=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(DonateForm, self).__init__(*args, **kwargs)

        choices = [
            ('1', "Anonymous"),
            ('2', "Other: "),
        ]
        self.user_id = None
        if user.username:
            self.user_id = user.id
            choices.insert(0, ('0', user.username))
            self.initial['donation_type'] = '0'
        else:
            self.initial['donation_type'] = '1'

        self.fields['donation_type'] = forms.ChoiceField(
                    widget=forms.RadioSelect(), choices=choices)

    def clean(self):
        try:
            if (not 'amount' in self.cleaned_data)\
                    or float(self.cleaned_data['amount']) < 1:
                raise forms.ValidationError('The amount must be more than 1')
        except ValueError:
            raise forms.ValidationError('The amount must be a valid number, use \'.\' for decimals')

        campaign = DonationCampaign.objects.order_by('date_start').last()
        returned_data = {
                "campaign_id": campaign.id,
                "display_amount": self.cleaned_data['show_amount']
                }

        annon = self.cleaned_data['donation_type']

        # We store the user even if the donation is annonymous
        if self.user_id :
            returned_data['user_id'] = self.user_id

        if annon == '1':
            returned_data['name'] = "Anonymous"
        elif annon == '2':
            returned_data['name'] = self.cleaned_data.get('name_option', '')
            if returned_data['name'] == '':
                raise forms.ValidationError('You have to enter a name to display')

        # Paypal gives only one field to add extra data so we send it as b64
        self.encoded_data = base64.b64encode(json.dumps(returned_data))
