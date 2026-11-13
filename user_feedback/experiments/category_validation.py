from django import forms
from django.conf import settings

from sounds.models import Sound
from user_feedback.experiments.base import SingleSoundExperiment, SingleSoundFeedbackForm


class CategoryValidationForm(SingleSoundFeedbackForm):
    """Yes/no form for the "Does this sound belong to this category?" question.

    Fields (plus the sound_id of SingleSoundFeedbackForm):
        answer: the user's yes/no response.
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


class CategoryValidation(SingleSoundExperiment):
    """A small inline box on the sound page asking whether the sound's assigned category is correct.
    A "no" also asks which category fits better, and both answers have an optional comment."""

    experiment_id = "category_validation"
    form_class = CategoryValidationForm
    inline_template = "user_feedback/inline_category_validation.html"

    def is_context_eligible(self, request, sound=None, **kwargs):
        # Only ask about sounds that have a category, given by the user or added automatically.
        return super().is_context_eligible(request, sound=sound, **kwargs) and all(sound.category_names)

    def inline_context(self, request, sound=None, **kwargs):
        # The box shows which category is being judged and offers a correction form.
        # bst_top_level_categories drives the category field, same as the describe form.
        return {
            **super().inline_context(request, sound=sound, **kwargs),
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
