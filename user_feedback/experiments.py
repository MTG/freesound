import hashlib

from django.conf import settings

from sounds.models import Sound
from user_feedback.forms import CategoryValidationForm
from user_feedback.models import UserFeedback


class Experiment:
    """Base class for a feedback experiment. One subclass = one experiment.

    An experiment is just code (no database table): it bundles what is specific to
    it, e.g. id, how many people see it, rules for when to show it. The shared logic 
    (auth check, sampling, throttling) lives here so every experiment behaves the same. 
    Subclasses override the small hooks below.
    """

    experiment_id = None          # unique id, also stored on each UserFeedback row
    form_class = None             # form the generic submit view validates for this experiment
    modal_template = None         # optional follow-up modal, rendered by the modal view

    @property
    def sample_rate(self):
        """Fraction of eligible people to show it to (from settings; 0.0 = off)."""
        return settings.FEEDBACK_SAMPLE_RATES.get(self.experiment_id, 0.0)

    def sampling_key(self, request):
        """What we sample on. Default = the user (stable per user).
        Override to sample per session, per sound, etc."""
        return str(request.user.id)

    def is_sampled_in(self, request):
        """True if this key falls inside the sample_rate slice. Deterministic:
        the same key always lands the same way, so people are not re-rolled on
        every page load."""
        rate = self.sample_rate
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            return False
        key = self.sampling_key(request)
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

    def is_throttled(self, request, **kwargs):
        """True if we should NOT show it because of 'do not nag' rules.
        Default: don't show again once the user has answered this experiment."""
        return UserFeedback.objects.filter(
            user=request.user, experiment_id=self.experiment_id
        ).exists()

    def should_show(self, request, **kwargs):
        """Determines whether it should be shown to the user at this moment."""
        if not request.user.is_authenticated:
            return False
        if not self.is_context_eligible(request, **kwargs):
            return False
        if self.is_throttled(request, **kwargs):
            return False
        if not self.is_sampled_in(request):
            return False
        return True

    def save_response(self, user, data):
        """Store one answer as a UserFeedback row."""
        return UserFeedback.objects.create(
            user=user, experiment_id=self.experiment_id, data=data
        )


class CategoryValidation(Experiment):
    """A small inline box on the sound page asking whether the sound's
    auto-assigned category is correct. The answer is just yes/no for now."""

    experiment_id = "category_validation"
    form_class = CategoryValidationForm
    modal_template = "user_feedback/modal_category_validation.html"

    def is_context_eligible(self, request, sound=None, **kwargs):
        # Only ask about sounds that actually have a category to validate.
        return bool(sound is not None and sound.bst_category)

    def modal_context(self, request, form):
        # The modal shows which category is being judged. Taken from the form so it
        # works both when first opened (initial) and when redisplayed with errors (POST).
        sound_id = form["sound_id"].value()
        sound = Sound.objects.filter(id=sound_id).first() if str(sound_id or "").isdigit() else None
        # bst_top_level_categories drives the category field, same as the describe form.
        return {"sound": sound, "bst_top_level_categories": settings.BST_CATEGORY_CHOICES}


# The registry: the single place experiments are listed. Add class + entry for a new experiment.
EXPERIMENTS = {
    CategoryValidation.experiment_id: CategoryValidation(),
}


def get_experiment(experiment_id):
    return EXPERIMENTS.get(experiment_id)
