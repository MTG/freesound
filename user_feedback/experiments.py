import hashlib
import uuid

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

from sounds.templatetags.bst_category import bst_taxonomy_category_names_to_category_key
from user_feedback.forms import CategoryFilterFeedbackForm, CategoryValidationForm
from user_feedback.models import FeedbackOptOut, UserFeedback
from utils.search.search_query_processor import SearchQueryProcessor


class Experiment:
    """Base class for a feedback experiment. One subclass = one experiment.

    An experiment is just code (no database table): it bundles what is specific to
    it, e.g. id, how many people see it, rules for when to show it. The shared logic
    (auth check, sampling, throttling) lives here so every experiment behaves the same.
    Subclasses override the small hooks below.
    """

    experiment_id = None  # unique id, also stored on each UserFeedback row
    form_class = None  # form the generic submit view validates for this experiment
    modal_template = None  # optional follow-up modal, rendered by the modal view
    inline_template = None  # optional inline box rendered on a host page
    page_url_name = None  # optional URL name of a page that loads the experiment after the page loads

    @property
    def sample_rate(self):
        """Fraction of eligible people to show it to (from settings; 0.0 = off)."""
        return settings.FEEDBACK_EXPERIMENTS.get(self.experiment_id, {}).get("sample_rate", 0.0)

    def sampling_key(self, request, **kwargs):
        """What we sample on. Default = the user (stable per user). Override to
        sample per session, per sound, etc.; kwargs carry the context passed to
        should_show (e.g. the sound)."""
        return str(request.user.id)

    def is_sampled_in(self, request, **kwargs):
        """True if this key falls inside the sample_rate slice. Deterministic:
        the same key always lands the same way, so people are not re-rolled on
        every page load."""
        rate = self.sample_rate
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            return False
        key = self.sampling_key(request, **kwargs)
        if not key:
            return False
        digest = hashlib.sha256(f"{self.experiment_id}:{key}".encode()).hexdigest()
        return (int(digest[:8], 16) % 10000) < rate * 10000

    def is_context_eligible(self, request, **kwargs):
        """Experiment-specific trigger condition (e.g. 'the sound has a category')."""
        return True

    def modal_context(self, request, form):
        """Extra template context for this experiment's modal, so the views that
        render it do not need to know what any experiment shows."""
        return {}

    def inline_context(self, request, **kwargs):
        """Extra template context for this experiment's inline box (its form, etc.),
        so the host page does not need to know what any experiment renders."""
        return {}

    def render_inline_html(self, request, **kwargs):
        """Rendered inline box for this request, or "" when it should not show now.
        The host page just outputs the string; all the wiring stays in here."""
        if self.inline_template is None or not self.should_show(request, **kwargs):
            return ""
        return mark_safe(
            render_to_string(self.inline_template, self.inline_context(request, **kwargs), request=request)
        )

    def render_page_items(self, request, sound_ids):
        """Returns the pieces of HTML to add to a page that shows `sound_ids` (see page_url_name).
        Each piece is a dict with "html" and, optionally, the "target" and "container" to place it."""
        return []

    def is_throttled(self, request, **kwargs):
        """True if we should NOT show it because of 'do not nag' rules.
        Default: don't show again once the user has opted out or answered."""
        if self.has_opted_out(request.user):
            return True
        return UserFeedback.objects.filter(user=request.user, experiment_id=self.experiment_id).exists()

    def should_show(self, request, **kwargs):
        """Determines whether it should be shown to the user at this moment."""
        if not request.user.is_authenticated:
            return False
        if not self.is_context_eligible(request, **kwargs):
            return False
        if self.is_throttled(request, **kwargs):
            return False
        if not self.is_sampled_in(request, **kwargs):
            return False
        return True

    def save_response(self, user, data, ip=None):
        """Store one answer as a UserFeedback row."""
        return UserFeedback.objects.create(user=user, experiment_id=self.experiment_id, data=data, ip=ip)

    def has_opted_out(self, user):
        """True if this user has permanently opted out of this experiment."""
        return FeedbackOptOut.objects.filter(user=user, experiment_id=self.experiment_id).exists()

    def opt_out(self, user):
        """Record a permanent 'don't ask again' for this experiment."""
        FeedbackOptOut.objects.get_or_create(user=user, experiment_id=self.experiment_id)


class CategoryValidation(Experiment):
    """A small inline box on the sound page asking whether the sound's assigned category is correct.
    A "no" also asks which category fits better, and both answers have an optional comment."""

    experiment_id = "category_validation"
    form_class = CategoryValidationForm
    inline_template = "user_feedback/inline_category_validation.html"

    def is_context_eligible(self, request, sound=None, **kwargs):
        # Only ask about sounds that actually have a category to validate.
        return bool(sound is not None and sound.bst_category)

    def inline_context(self, request, sound=None, **kwargs):
        # The box shows which category is being judged and offers a correction form.
        # bst_top_level_categories drives the category field, same as the describe form.
        return {
            "sound": sound,
            "category_validation_form": self.form_class(initial={"sound_id": sound.id}),
            "bst_top_level_categories": settings.BST_CATEGORY_CHOICES,
        }

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


class CategoryFilterFeedback(Experiment):
    """Experiment in the search page, shown when the results are filtered by category.
    It asks how useful the category filter was (1-5 rating with an optional comment),
    and whether each result of the page is what the user was looking for (yes/no)."""

    experiment_id = "category_filter_feedback"
    form_class = CategoryFilterFeedbackForm
    inline_template = "user_feedback/inline_category_filter_feedback.html"
    result_template = "user_feedback/inline_category_filter_result.html"
    page_url_name = "sounds-search"
    result_container = "[data-score]"  # Element of the search page that wraps one result
    bar_delay_seconds = 0  # Seconds to wait before showing the overall rating bar

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
        context = {"experiment_id": self.experiment_id, "search": search}

        # The results of the page that are not answered yet get the yes/no question.
        answered_sound_ids = self._answered_sound_ids(request.user, search)
        items = [
            self._question_item(request, context, sound_id, position)
            for position, sound_id in enumerate(sound_ids, start=1)
            if sound_id not in answered_sound_ids
        ]
        # The overall rating bar is shown until the user rates this search.
        context["show_bar"] = not self._is_rated(request.user, search)
        context["bar_delay_seconds"] = self.bar_delay_seconds
        # Key of the category (e.g. "m-sp"), to link to its description in the taxonomy page.
        context["category_key"] = bst_taxonomy_category_names_to_category_key(
            search["category"], search["subcategory"] or None
        )
        if not items and not context["show_bar"]:
            return []
        # The info about the search and the bar go at the end of the page.
        return items + [{"html": render_to_string(self.inline_template, context, request=request)}]


# The registry is built from settings.FEEDBACK_EXPERIMENTS, the place experiments are.
EXPERIMENTS = {
    experiment_id: import_string(config["class"])() for experiment_id, config in settings.FEEDBACK_EXPERIMENTS.items()
}


def get_experiment(experiment_id):
    return EXPERIMENTS.get(experiment_id)
