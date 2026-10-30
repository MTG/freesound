import uuid

from django import forms
from django.template.loader import render_to_string

from sounds.models import Sound
from sounds.templatetags.bst_category import bst_taxonomy_category_names_to_category_key
from user_feedback.experiments.base import Experiment
from user_feedback.models import UserFeedback
from utils.search.search_query_processor import SearchQueryProcessor


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
        played_sounds: hidden field with the sounds played in the page before answering,
            each with the second of its first play and its number of plays.
        seconds_in_page: hidden field with the seconds from the page load to the answer.
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

    # Info about the plays filled by experiments.js
    played_sounds = forms.CharField(required=False, max_length=2000)
    seconds_in_page = forms.IntegerField(required=False, min_value=0)

    def clean_result_ids(self):
        # Sound IDs are sent as "9,99,1999" and saved as a list.
        try:
            return [int(sound_id) for sound_id in self.cleaned_data["result_ids"].split(",")]
        except ValueError:
            raise forms.ValidationError("Invalid list of results.")

    def clean_played_sounds(self):
        # Plays are sent as "2:9:8" and saved as a list of [sound id, seconds, times played].
        # A wrong list is saved as None (not known).
        played_sounds = self.cleaned_data["played_sounds"]
        if not played_sounds:
            return []
        try:
            plays = [[int(value) for value in play.split(":")] for play in played_sounds.split(",")]
        except ValueError:
            return None
        if any(len(play) != 3 for play in plays):
            return None
        return plays

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


class CategoryFilterFeedback(Experiment):
    """Experiment in the search page, shown when the results are filtered by category.
    It asks how useful the category filter was (1-5 rating with an optional comment),
    and whether each result of the page is what the user was looking for (yes/no)."""

    experiment_id = "category_filter_feedback"
    form_class = CategoryFilterFeedbackForm
    inline_template = "user_feedback/inline_category_filter_feedback.html"
    result_template = "user_feedback/inline_category_filter_result.html"
    loads_after_page = True
    result_container = "[data-score]"  # Element of the search page that wraps one result
    # The overall rating bar is shown after X different sounds are played, and then Y seconds.
    # The question of a result is shown when its sound is played, or with the bar.
    bar_plays = 2
    bar_delay_seconds = 2

    @staticmethod
    def _filter_value(sqp, field_name):
        """Returns the value of a filter of the search (e.g. "Music" for category), or "" if not set."""
        for field, value in sqp.non_option_filters:
            if field == field_name:
                return value.strip('"')
        return ""

    def is_context_eligible(self, request, sqp=None, sound_ids=None, **kwargs):
        # Only for a list of sounds filtered by category (not the map, not packs).
        if sqp is None or sqp.errors or not sound_ids or not sqp.has_category_filter():
            return False
        return not sqp.map_mode_active() and not sqp.display_as_packs_active()

    def sampling_key(self, request, sqp=None, **kwargs):
        # Per search (user, category and query), so a user is asked in some of their searches.
        if sqp is None:
            return ""
        category = self._filter_value(sqp, "category")
        query = sqp.get_option_value_to_apply("query") or ""
        return f"{request.user.id}:{category}:{query}"

    def is_throttled(self, request, **kwargs):
        # Only the opt-out hides everything. Results already answered are skipped in render_page_items.
        return self.has_opted_out(request.user)

    def _search_info(self, sqp, sound_ids):
        """Returns the info about the search that is sent with every answer."""
        return {
            "category": self._filter_value(sqp, "category"),
            "subcategory": self._filter_value(sqp, "subcategory"),
            "query": sqp.get_option_value_to_apply("query") or "",
            "search_filter": sqp.get_filter_string_for_url(),
            "sort": sqp.get_option_value_to_apply("sort_by") or "",
            "page": sqp.get_option_value_to_apply("page"),
            "result_ids": ",".join(str(sound_id) for sound_id in sound_ids),
            "search_url": sqp.get_url(),
            "search_id": uuid.uuid4().hex,
        }

    def _answered_sound_ids(self, user, search):
        """Returns the sounds that the user already answered for this category, subcategory and query."""
        answers = UserFeedback.objects.filter(
            user=user,
            experiment_id=self.experiment_id,
            data__kind="result",
            data__category=search["category"],
            data__subcategory=search["subcategory"],
            data__query=search["query"],
        )
        return set(answers.values_list("data__sound_id", flat=True))

    def _is_rated(self, user, search):
        """Returns True if the user already rated this search (same category, subcategory and query)."""
        return UserFeedback.objects.filter(
            user=user,
            experiment_id=self.experiment_id,
            data__kind="overall",
            data__category=search["category"],
            data__subcategory=search["subcategory"],
            data__query=search["query"],
        ).exists()

    def _question_item(self, request, context, sound_id, position):
        """Returns the yes/no question of one result, to be placed right after the sound."""
        context = {**context, "sound_id": sound_id, "position": position}
        return {
            "target": f'[data-sound-id="{sound_id}"]',
            "container": self.result_container,
            "html": render_to_string(self.result_template, context, request=request),
        }

    def render_page_items(self, request, sound_ids):
        """Returns the pieces of HTML of the experiment for a search page that shows `sound_ids`.
        The request has the same GET parameters as the search page."""
        sqp = SearchQueryProcessor(request)
        if not self.should_show(request, sqp=sqp, sound_ids=sound_ids):
            return []
        search = self._search_info(sqp, sound_ids)
        # Rating a search closes its questions, so a rated search is not asked again.
        if self._is_rated(request.user, search):
            return []
        context = {
            "experiment_id": self.experiment_id,
            "config": self.config,
            "search": search,
            "bar_plays": self.bar_plays,
            "bar_delay_seconds": self.bar_delay_seconds,
        }

        # The results of the page that are not answered yet get the yes/no question.
        answered_sound_ids = self._answered_sound_ids(request.user, search)
        items = [
            self._question_item(request, context, sound_id, position)
            for position, sound_id in enumerate(sound_ids, start=1)
            if sound_id not in answered_sound_ids
        ]
        # Key of the category (e.g. "m-sp"), to link to its description in the taxonomy page.
        context["category_key"] = bst_taxonomy_category_names_to_category_key(
            search["category"], search["subcategory"] or None
        )
        # The info about the search and the bar go at the end of the page.
        return items + [{"html": render_to_string(self.inline_template, context, request=request)}]
