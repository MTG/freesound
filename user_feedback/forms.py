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
    """Form for the two questions of the category filter experiment (search page).

    Fields:
        kind: which question is answered, "overall" or "result".
        rating: the user's 1-5 response. Required when kind is "overall".
        text: optional free-text comment.
        answer: the user's yes/no response. Required when kind is "result".
        sound_id: hidden field identifying the sound of the result.
        position: hidden field with the position of the sound in the page of results.
        category, subcategory, query, search_filter, sort, page, result_ids, search_url, search_id:
            hidden fields describing the search.
    """

    KIND_CHOICES = [("overall", "Overall"), ("result", "Result")]
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    ANSWER_CHOICES = [("yes", "Yes"), ("no", "No")]
    # Fields used by each kind of answer.
    KIND_FIELDS = {"overall": ["rating", "text"], "result": ["answer", "sound_id", "position"]}
    OPTIONAL_FIELDS = ["text"]

    kind = forms.ChoiceField(choices=KIND_CHOICES)

    rating = forms.TypedChoiceField(choices=RATING_CHOICES, coerce=int, required=False, empty_value=None)
    text = forms.CharField(required=False, max_length=2000)

    answer = forms.ChoiceField(choices=ANSWER_CHOICES, required=False)
    sound_id = forms.IntegerField(required=False)
    position = forms.IntegerField(required=False, min_value=1)

    # Search info filled in by the server
    category = forms.CharField(max_length=200)
    subcategory = forms.CharField(required=False, max_length=200)
    query = forms.CharField(required=False, max_length=1000)
    search_filter = forms.CharField(required=False, max_length=2000)
    sort = forms.CharField(required=False, max_length=100)
    page = forms.IntegerField(min_value=1)
    result_ids = forms.CharField(max_length=2000)
    search_url = forms.CharField(required=False, max_length=4000)
    search_id = forms.CharField(max_length=32)

    def clean_result_ids(self):
        # Sound IDs are sent as "9,99,1999" and saved as a list.
        try:
            return [int(sound_id) for sound_id in self.cleaned_data["result_ids"].split(",")]
        except ValueError:
            raise forms.ValidationError("Invalid list of results.")

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get("kind")
        if kind is None:
            return cleaned_data
        # Required fields of this kind.
        for field in self.KIND_FIELDS[kind]:
            if field not in self.OPTIONAL_FIELDS and cleaned_data.get(field) in (None, ""):
                self.add_error(field, "This field is required.")
        # Check that the sound exists.
        sound_id = cleaned_data.get("sound_id")
        if kind == "result" and sound_id and not Sound.objects.filter(id=sound_id).exists():
            self.add_error("sound_id", "Unknown sound.")
        # Do not save the fields of the other kind.
        other_kind = "result" if kind == "overall" else "overall"
        for field in self.KIND_FIELDS[other_kind]:
            cleaned_data.pop(field, None)
            self.errors.pop(field, None)
        return cleaned_data
