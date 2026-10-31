import uuid

from django import forms

from sounds.templatetags.bst_category import bst_taxonomy_category_names_to_category_key
from user_feedback.experiments.base import SoundListExperiment, SoundListFeedbackForm


class CategoryFilterFeedbackForm(SoundListFeedbackForm):
    """Form of the category filter experiment: the questions of SoundListFeedbackForm, plus
    category, subcategory, query, search_filter, sort, page, search_url and search_id, the
    hidden fields describing the search."""

    # Search info filled in by the server
    category = forms.CharField(max_length=200)
    subcategory = forms.CharField(required=False, max_length=200)
    query = forms.CharField(required=False, max_length=1000)
    search_filter = forms.CharField(required=False, max_length=2000)
    sort = forms.CharField(required=False, max_length=100)
    page = forms.IntegerField(min_value=1)
    search_url = forms.CharField(required=False, max_length=4000)
    search_id = forms.CharField(max_length=32)


class CategoryFilterFeedback(SoundListExperiment):
    """Experiment in the search page, shown when the results are filtered by category.
    It asks how useful the category filter was (1-5 rating with an optional comment),
    and whether each result of the page is what the user was looking for (yes/no).
    The search page places it with {% feedback_experiment "category_filter_feedback" docs=docs sqp=sqp %}."""

    experiment_id = "category_filter_feedback"
    form_class = CategoryFilterFeedbackForm
    bar_template = "user_feedback/category_filter_feedback_bar.html"
    result_container = "[data-score]"  # Element of the search page that wraps one result

    @staticmethod
    def _filter_value(sqp, field_name):
        """Returns the value of a filter of the search (e.g. "Music" for category), or "" if not set."""
        for field, value in sqp.non_option_filters:
            if field == field_name:
                return value.strip('"')
        return ""

    def get_sounds(self, docs=None, **kwargs):
        # The results of the search page have their sound (unless they are packs).
        return [doc["sound"] for doc in docs or [] if "sound" in doc]

    def is_context_eligible(self, request, sqp=None, **kwargs):
        # Only for a list of sounds filtered by category (not the map, not packs).
        if sqp is None or sqp.errors or not sqp.has_category_filter():
            return False
        if sqp.map_mode_active() or sqp.display_as_packs_active():
            return False
        return super().is_context_eligible(request, sqp=sqp, **kwargs)

    def list_key(self, sqp=None, **kwargs):
        # The same category, subcategory and query is the same search, in any page or sorting.
        return {
            "category": self._filter_value(sqp, "category"),
            "subcategory": self._filter_value(sqp, "subcategory"),
            "query": sqp.get_option_value_to_apply("query") or "",
        }

    def list_info(self, sqp=None, **kwargs):
        return {
            "search_filter": sqp.get_filter_string_for_url(),
            "sort": sqp.get_option_value_to_apply("sort_by") or "",
            "page": sqp.get_option_value_to_apply("page"),
            "search_url": sqp.get_url(),
            "search_id": uuid.uuid4().hex,
        }

    def overall_context(self, info, **kwargs):
        # Key of the category (e.g. "m-sp"), to link to its description in the taxonomy page.
        return {
            "category_key": bst_taxonomy_category_names_to_category_key(info["category"], info["subcategory"] or None)
        }
