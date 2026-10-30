import hashlib

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from sounds.models import Sound
from user_feedback.models import FeedbackExperiment, FeedbackOptOut, UserFeedback


class Experiment:
    """Base class for a feedback experiment. One subclass = one experiment.

    An experiment is just code (no database table): it bundles what is specific to
    it, e.g. id, how many people see it, rules for when to show it. The shared logic
    (auth check, sampling, throttling) lives here so every experiment behaves the same.
    Subclasses override the small hooks below.
    """

    experiment_id = None  # unique id, also stored on each UserFeedback row
    form_class = None  # form the generic submit view validates for this experiment
    # Optional inline box, placed in a template with {% feedback_experiment "<experiment_id>" ... %}
    inline_template = None
    page_url_name = None  # optional URL name of a page that loads the experiment after the page loads

    @property
    def config(self):
        """Configuration of the experiment that is edited in the admin (sample rate and texts)."""
        return FeedbackExperiment.objects.filter(experiment_id=self.experiment_id).first()

    @property
    def sample_rate(self):
        """Fraction of eligible people to show it to (0.0 = off)."""
        config = self.config
        return config.sample_rate if config else 0.0

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
        # Experiments are only shown to logged-in users.
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


class SingleSoundFeedbackForm(forms.Form):
    """Base form of the experiments about a single sound (see SingleSoundExperiment).

    Fields:
        sound_id: hidden field identifying the sound.
    """

    # Sound ID filled in by the server
    sound_id = forms.IntegerField(widget=forms.HiddenInput)

    def clean_sound_id(self):
        # A hidden field can be edited by the user, so confirm it is a real sound.
        sound_id = self.cleaned_data["sound_id"]
        if not Sound.objects.filter(id=sound_id).exists():
            raise forms.ValidationError("Unknown sound.")
        return sound_id


class SingleSoundExperiment(Experiment):
    """Base class for an experiment about a single sound, shown in an inline box placed with
    {% feedback_experiment "<experiment_id>" sound=sound %}. A user is asked about each sound at
    most once, and sampling is per sound, so every user can be asked about some of the sounds."""

    form_class = SingleSoundFeedbackForm

    def is_context_eligible(self, request, sound=None, **kwargs):
        return sound is not None

    def inline_context(self, request, sound=None, **kwargs):
        # The box gets the sound and the form of the experiment, with the sound filled in.
        return {
            "config": self.config,
            "sound": sound,
            "form": self.form_class(initial={"sound_id": sound.id}),
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
