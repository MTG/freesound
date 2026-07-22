from django import forms
from django.conf import settings

from sounds.models import Sound


class CategoryValidationForm(forms.Form):
    """Yes/no form for the "Does this sound belong to this category?" question.

    Fields:
        answer: the user's yes/no response.
        sound_id: hidden field identifying the sound.
        selected_category: which category fits better. Required when answer is "no".
        text: optional free-text comment.

    The inline box saves nothing on click: each answer opens a follow-up modal, and
    the row is only stored when that modal's Send is pressed. Both modals collect the
    optional `text`; the "no" modal also asks for `selected_category`. Keeping every
    field on one form means the same generic submit endpoint handles both answers.
    `selected_category` is declared required=False at field level (so a "yes"
    submission validates without it) and is enforced in clean() only when the answer
    is "no".
    """

    ANSWER_CHOICES = [("yes", "Yes"), ("no", "No")]

    answer = forms.ChoiceField(
        choices=ANSWER_CHOICES,
        widget=forms.RadioSelect,
        label="Does this sound belong to this category?",
    )

    # Sound ID filled in by the server
    sound_id = forms.IntegerField(widget=forms.HiddenInput)

    # Asked only in the "no" modal (the correction). Subcategory level, same choices
    # as the upload/describe form so the modal can reuse its category field.
    # required=False so a "yes" submission validates without it; clean() then makes
    # it compulsory when the answer is "no".
    selected_category = forms.ChoiceField(
        choices=settings.BST_SUBCATEGORY_CHOICES,
        required=False,
        label="Which category fits better?",
    )
    # Optionally, an answer can be sent without writing anything.
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 1}),
        max_length=2000,
        label="Anything else? (optional)",
    )

    def clean_sound_id(self):
        # A hidden field can be edited by the user, so confirm it is a real sound.
        sound_id = self.cleaned_data["sound_id"]
        if not Sound.objects.filter(id=sound_id).exists():
            raise forms.ValidationError("Unknown sound.")
        return sound_id

    def clean(self):
        # "No" means the category is wrong, so a corrected one is required; "yes" is not.
        cleaned_data = super().clean()
        if cleaned_data.get("answer") == "no" and not cleaned_data.get("selected_category"):
            self.add_error("selected_category", "Please choose the category that fits better.")
        return cleaned_data
