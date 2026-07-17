from django import forms


class CategoryValidationForm(forms.Form):
    """Yes/no form for the "Does this sound belong to this category?" question.

    Fields:
        answer: the user's yes/no response.
        sound_id: hidden field identifying the sound.
    """

    ANSWER_CHOICES = [("yes", "Yes"), ("no", "No")]

    answer = forms.ChoiceField(
        choices=ANSWER_CHOICES,
        widget=forms.RadioSelect,
        label="Does this sound belong to this category?",
    )

    # Sound ID filled in by the server
    sound_id = forms.IntegerField(widget=forms.HiddenInput)
