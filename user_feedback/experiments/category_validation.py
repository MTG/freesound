from django import forms
from django.conf import settings

from sounds.models import Sound
from user_feedback.experiments.base import Experiment
from user_feedback.models import UserFeedback


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


class CategoryValidation(Experiment):
    """A small inline box on the sound page asking whether the sound's assigned category is correct.
    A "no" also asks which category fits better, and both answers have an optional comment."""

    experiment_id = "category_validation"
    form_class = CategoryValidationForm
    inline_template = "user_feedback/inline_category_validation.html"
    inline_page = "sound_page"

    def is_context_eligible(self, request, sound=None, **kwargs):
        # Only ask about sounds that have a category, given by the user or added automatically.
        return bool(sound is not None and all(sound.category_names))

    def inline_context(self, request, sound=None, **kwargs):
        # The box shows which category is being judged and offers a correction form.
        # bst_top_level_categories drives the category field, same as the describe form.
        return {
            "config": self.config,
            "sound": sound,
            "category_validation_form": self.form_class(initial={"sound_id": sound.id}),
            "bst_top_level_categories": settings.BST_CATEGORY_CHOICES,
        }

    def save_response(self, user, data, ip=None):
        # Save the category that was asked about and its source.
        # "u" = user gave it, "a" = automatically added.
        sound = Sound.objects.get(id=data["sound_id"])
        data = {
            **data,
            "sound_category": sound.category_code,
            "sound_category_source": "u" if sound.bst_category else "a",
        }
        return super().save_response(user, data, ip=ip)

    def is_throttled(self, request, sound=None, **kwargs):
        # Opt-out wins over everything: "don't ask again" hides the box on every sound.
        if self.has_opted_out(request.user):
            return True
        # Otherwise once per sound per user: match on user + the sound_id saved in data,
        # so a user answers each sound at most once but is still asked about other sounds.
        if sound is None:
            return True
        return UserFeedback.objects.filter(
            user=request.user, experiment_id=self.experiment_id, data__sound_id=sound.id
        ).exists()

    def sampling_key(self, request, sound=None, **kwargs):
        # Sample per (user, sound), not per user: the rate gates each sound a user
        # opens, so every user can be asked (on ~rate of the sounds they open),
        # rather than a fixed cohort seeing it on all their sounds.
        return f"{request.user.id}:{sound.id}" if sound else ""
