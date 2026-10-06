import hashlib

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

from user_feedback.forms import CategoryFilterFeedbackForm, CategoryValidationForm
from user_feedback.models import FeedbackOptOut, UserFeedback


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
    """Search-page popup asking how useful it was to filter results by a category facet.

    Measures the overall usefulness of the category filter. Shown only when the user is browsing
    results that are filtered by a category, and once they have seen a filtered result set (handled in the search view).
    """

    experiment_id = "category_filter_feedback"
    form_class = CategoryFilterFeedbackForm
    modal_template = "user_feedback/modal_category_filter_feedback.html"

    def is_context_eligible(self, request, sqp=None, **kwargs):
        # Only when a category facet is actually applied to the current search.
        return bool(sqp is not None and sqp.has_category_filter())

    def sampling_key(self, request, category=None, **kwargs):
        # Per (user, category): every user stays "in play" (the rate gates each category a user
        # filters by, rather than fixing a permanent cohort of users).
        return f"{request.user.id}:{category}" if category else ""

    def is_throttled(self, request, category=None, **kwargs):
        # Opt-out hides it everywhere; otherwise ask at most once per category per user.
        if self.has_opted_out(request.user):
            return True
        if not category:
            return True
        return UserFeedback.objects.filter(
            user=request.user, experiment_id=self.experiment_id, data__category=category
        ).exists()


# The registry is built from settings.FEEDBACK_EXPERIMENTS, the place experiments are.
EXPERIMENTS = {
    experiment_id: import_string(config["class"])() for experiment_id, config in settings.FEEDBACK_EXPERIMENTS.items()
}


def get_experiment(experiment_id):
    return EXPERIMENTS.get(experiment_id)
