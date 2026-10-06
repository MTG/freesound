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

    The inline box saves nothing on click: clicking an answer expands the box (the
    "no" answer also reveals the category picker) and only Send stores the row.
    Keeping every field on one form means the same generic submit endpoint handles
    both answers. `selected_category` is declared required=False at field level (so a
    "yes" submission validates without it) and is enforced in clean() only when the
    answer is "no".
    """

    ANSWER_CHOICES = [("yes", "Yes"), ("no", "No")]
    # Error message if no category and/or subcategory is picked.
    CATEGORY_REQUIRED_MESSAGE = "Please choose a category and subcategory."

    answer = forms.ChoiceField(
        choices=ANSWER_CHOICES,
        widget=forms.RadioSelect,
        label="Does this sound belong to the category above?",
    )

    # Sound ID filled in by the server
    sound_id = forms.IntegerField(widget=forms.HiddenInput)

    # Asked only for the "no" answer (the correction). Subcategory level, same choices
    # as the upload/describe form so the box can reuse its category field.
    # required=False so a "yes" submission validates without it; clean() then makes
    # it compulsory when the answer is "no".
    selected_category = forms.ChoiceField(
        choices=settings.BST_SUBCATEGORY_CHOICES,
        required=False,
        label="Which category fits better?",
        error_messages={"invalid_choice": CATEGORY_REQUIRED_MESSAGE},
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
            self.add_error("selected_category", self.CATEGORY_REQUIRED_MESSAGE)
        # "yes" never stores a category; drops any left over from an earlier "no".
        if cleaned_data.get("answer") == "yes":
            cleaned_data["selected_category"] = ""
            self.errors.pop("selected_category", None)
        return cleaned_data


class CategoryFilterFeedbackForm(forms.Form):
    """Rating form for the search-page "category filter" popup.

    Fields:
        rating: 1-5 usefulness rating of filtering results by the current category facet.
        text: optional free-text comment.
        category / query: hidden context, filled in by the server (the modal URL), stored on
            the row so the answer can be analysed per category and per query. Not user-editable.
    """

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="How useful was filtering by this category?",
    )
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 1}),
        max_length=2000,
        label="Anything else? (optional)",
    )

    # Server-supplied context (hidden). category drives the per-(user, category) throttle.
    category = forms.CharField(widget=forms.HiddenInput)
    query = forms.CharField(required=False, widget=forms.HiddenInput)
