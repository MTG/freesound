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
    """Base form of the experiments about a list of sounds (see SoundListExperiment). An answer is
    either to the yes/no question of one sound (kind "sound") or to the overall question (kind "overall").

    Experiments add the fields of their overall question, listed in OVERALL_FIELDS, and the fields of
    the info about their list (see SoundListExperiment.list_key and list_info). The fields of the other
    kind of answer are removed, so they are neither validated nor saved.

    Fields:
        kind: which question is answered, "sound" (question of one sound) or "overall".
        answer: the user's yes/no answer to the question of one sound.
        sound_id: hidden field identifying the sound.
        position: hidden field with the position of the sound in the list.
        list_sound_ids: hidden field with the sounds of the list.
        played_sounds: hidden field with the sounds played in the page before answering,
            each with the second of its first play and its number of plays.
        seconds_in_page: hidden field with the seconds from the page load to the answer.
    """

    KIND_CHOICES = [("sound", "Sound question"), ("overall", "Overall question")]
    ANSWER_CHOICES = [("yes", "Yes"), ("no", "No")]
    SOUND_QUESTION_FIELDS = ["answer", "sound_id", "position"]
    OVERALL_FIELDS = []  # Fields of the overall question, defined by each experiment

    kind = forms.ChoiceField(choices=KIND_CHOICES)

    # Yes/no question of one sound
    answer = forms.ChoiceField(choices=ANSWER_CHOICES)
    sound_id = forms.IntegerField()
    position = forms.IntegerField(min_value=1)

    # Sounds of the list filled in by the server
    list_sound_ids = forms.CharField(max_length=2000)

    # Info about the plays filled by experiments.js
    played_sounds = forms.CharField(required=False, max_length=2000)
    seconds_in_page = forms.IntegerField(required=False, min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep only the fields of the question that is answered.
        kind = self.data.get("kind")
        other_fields = {"sound": self.OVERALL_FIELDS, "overall": self.SOUND_QUESTION_FIELDS}.get(kind, [])
        for field in other_fields:
            del self.fields[field]

    def clean_sound_id(self):
        sound_id = self.cleaned_data["sound_id"]
        if not Sound.objects.filter(id=sound_id).exists():
            raise forms.ValidationError("Unknown sound.")
        return sound_id

    def clean_list_sound_ids(self):
        # Sound IDs are sent as "9,99,1999" and saved as a list.
        try:
            return [int(sound_id) for sound_id in self.cleaned_data["list_sound_ids"].split(",")]
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


class SoundListExperiment(Experiment):
    """Base class for an experiment about a list of sounds shown in a page, placed with
    {% feedback_experiment "<experiment_id>" sounds=sounds ... %}. It asks two kinds of questions:
      - Sound question: a yes/no question (sound_question) after the player of each sound of the list.
        experiments.js places it after the sound, and shows it when the sound is played. It is not
        asked again for a sound already answered in the same list.
      - Overall question: a question about the whole list, shown in a toast at the bottom of the page
        after overall_question_plays sounds of the list are played (and overall_question_delay_seconds).
        Each experiment writes it: its fields (in the form, see SoundListFeedbackForm.OVERALL_FIELDS)
        and its template (overall_question_template). Answering it closes the questions of the list,
        and the same list is not asked again.

    The arguments of the tag are passed to the hooks below, so the page gives the experiment what
    it needs to know about the list (e.g. the search), and the experiment knows nothing about pages.
    """

    form_class = SoundListFeedbackForm
    inline_template = "user_feedback/sound_list.html"

    # Sound question
    sound_question = "Is this what you were looking for?"
    sound_question_template = "user_feedback/sound_list_sound_question.html"
    # Selector of the element of the page that wraps each sound of the list. The sound question is placed after it.
    sound_container = None

    # Overall question, shown in a toast. Its template has the question and the inputs of the overall
    # fields of the form, and is rendered with the context of inline_context (see overall_context).
    overall_question_template = None
    # Name of the field of the overall question set by the buttons with [data-experiment-answer].
    overall_answer_field = None
    # The toast is shown after X different sounds of the page are played, and then Y seconds.
    overall_question_plays = 2
    overall_question_delay_seconds = 2

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
        """Returns extra template context for the overall question."""
        return {}

    def is_context_eligible(self, request, **kwargs):
        return bool(self.get_sounds(**kwargs))

    def is_throttled(self, request, **kwargs):
        # Opt-out hides everything, and answering the overall question closes the questions of the
        # list. Sounds already answered are skipped in inline_context.
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
            "list_sound_ids": ",".join(str(sound.id) for sound in sounds),
        }
        # The sounds of the list that are not answered yet get the sound question.
        answered_sound_ids = set(self._answers(request.user, key, "sound").values_list("data__sound_id", flat=True))
        sound_questions = [
            {"sound_id": sound.id, "position": position}
            for position, sound in enumerate(sounds, start=1)
            if sound.id not in answered_sound_ids
        ]
        return {
            "experiment_id": self.experiment_id,
            "config": self.config,
            "info": info,
            "sound_questions": sound_questions,
            "sound_question": self.sound_question,
            "sound_question_template": self.sound_question_template,
            "sound_container": self.sound_container,
            "overall_question_template": self.overall_question_template,
            "overall_answer_field": self.overall_answer_field,
            "overall_question_plays": self.overall_question_plays,
            "overall_question_delay_seconds": self.overall_question_delay_seconds,
            **self.overall_context(info, **kwargs),
        }
