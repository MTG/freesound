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


class SoundListFeedbackForm(forms.Form):
    """Base form of the experiments about a list of sounds (see SoundListExperiment).
    Experiments add the fields of the info about their list (see SoundListExperiment.list_info).

    Fields:
        kind: which question is answered, "overall" or "result".
        rating: the user's 1-5 response. Required when kind is "overall".
        text: optional free-text comment.
        answer: the user's yes/no response. Required when kind is "result".
        sound_id: hidden field identifying the sound of the result.
        position: hidden field with the position of the sound in the list.
        result_ids: hidden field with the sounds of the list.
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

    # Sounds of the list filled in by the server
    result_ids = forms.CharField(max_length=2000)

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


class SoundListExperiment(Experiment):
    """Base class for an experiment about a list of sounds shown in a page, placed with
    {% feedback_experiment "<experiment_id>" sounds=sounds ... %}. It asks:
      - for each sound of the list, a yes/no question, placed after the sound by experiments.js.
        It is shown when its sound is played, or with the overall question.
      - an overall 1-5 rating with an optional comment, in a bar at the bottom of the page shown
        after some sounds are played. Rating a list closes its questions and it is not asked again.

    The arguments of the tag are passed to the hooks below, so the page gives the experiment what
    it needs to know about the list (e.g. the search), and the experiment knows nothing about pages.
    """

    form_class = SoundListFeedbackForm
    inline_template = "user_feedback/sound_list.html"
    bar_template = None  # overall question bar, rendered with the context of inline_context
    result_template = "user_feedback/sound_list_result.html"  # question of one sound
    result_question = "Is this what you were looking for?"
    result_container = None  # selector of the element of the page that wraps one sound of the list
    # The overall rating bar is shown after X different sounds are played, and then Y seconds.
    bar_plays = 2
    bar_delay_seconds = 2

    def get_sounds(self, sounds=None, **kwargs):
        """Returns the sounds of the list, in the order of the page. Default: the `sounds` argument."""
        return sounds or []

    def list_key(self, **kwargs):
        """Returns the info that identifies the list (e.g. the query of a search), as a dict.
        It is saved with every answer, and a list with the same key is not asked twice."""
        return {}

    def list_info(self, **kwargs):
        """Returns more info about the list to save with every answer, as a dict."""
        return {}

    def overall_context(self, info, **kwargs):
        """Returns extra template context for the overall question bar."""
        return {}

    def is_context_eligible(self, request, **kwargs):
        return bool(self.get_sounds(**kwargs))

    def is_throttled(self, request, **kwargs):
        # Opt-out hides everything, and rating a list closes its questions. Sounds already
        # answered are skipped in inline_context.
        if self.has_opted_out(request.user):
            return True
        return self._answers(request.user, self.list_key(**kwargs), "overall").exists()

    def sampling_key(self, request, **kwargs):
        # Per list, so a user is asked in some of the lists they see.
        return ":".join(str(value) for value in [request.user.id, *self.list_key(**kwargs).values()])

    def _answers(self, user, key, kind):
        """Returns the answers of the user of this kind for the list with this key."""
        filters = {f"data__{field}": value for field, value in key.items()}
        return UserFeedback.objects.filter(user=user, experiment_id=self.experiment_id, data__kind=kind, **filters)

    def inline_context(self, request, **kwargs):
        sounds = self.get_sounds(**kwargs)
        key = self.list_key(**kwargs)
        info = {
            **key,
            **self.list_info(**kwargs),
            "result_ids": ",".join(str(sound.id) for sound in sounds),
        }
        # The sounds of the list that are not answered yet get the yes/no question.
        answered_sound_ids = set(self._answers(request.user, key, "result").values_list("data__sound_id", flat=True))
        questions = [
            {"sound_id": sound.id, "position": position}
            for position, sound in enumerate(sounds, start=1)
            if sound.id not in answered_sound_ids
        ]
        return {
            "experiment_id": self.experiment_id,
            "config": self.config,
            "info": info,
            "questions": questions,
            "result_template": self.result_template,
            "result_question": self.result_question,
            "result_container": self.result_container,
            "bar_template": self.bar_template,
            "bar_plays": self.bar_plays,
            "bar_delay_seconds": self.bar_delay_seconds,
            **self.overall_context(info, **kwargs),
        }
