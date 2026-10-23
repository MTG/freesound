from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserFeedback(models.Model):
    """One row of user feedback, for ANY experiment.

    A single generic table shared by every experiment. What makes a row
    experiment-specific is:
      - ``experiment_id``: which experiment it belongs to (e.g. "category_validation")
      - ``data``: a free-form JSON blob with that experiment's answers/context

    So adding a new experiment never needs a new table or migration -- it just
    writes rows with a different ``experiment_id`` and a different ``data`` shape.
    """

    experiment_id = models.CharField(max_length=100, db_index=True)
    # Optional, so anonymous users can leave feedback too.
    # SET_NULL keeps the feedback row even if the account is later deleted.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_feedback",
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        who = self.user or self.ip or "anonymous"
        return f"{who} / {self.experiment_id} @ {self.created:%Y-%m-%d}"


class FeedbackOptOut(models.Model):
    """A row exists <=> this user opted out of this experiment ("don't ask again").

    The presence of the row IS the preference. Kept generic (keyed by experiment_id) so every experiment
    shares this one table; opt-outs live here, separate from the UserFeedback answers.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback_opt_outs")
    experiment_id = models.CharField(max_length=100, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "experiment_id")

    def __str__(self):
        return f"{self.user} opted out of {self.experiment_id}"


class FeedbackExperiment(models.Model):
    """Configuration of one experiment that can be changed in the admin.

    The code of each experiment is in experiments.py (see settings.FEEDBACK_EXPERIMENTS).
    This model has what does not need a code change: how often it is shown and the texts of its information modal.
    """

    experiment_id = models.CharField(max_length=100, unique=True)
    sample_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Fraction of the eligible views that show the experiment (0 = off, 1 = every view).",
    )
    title = models.CharField(max_length=200, help_text="Name of the study, shown in the information modal.")
    description = models.TextField(
        help_text="Description of the study, shown in the information modal. It can have HTML links."
    )

    def __str__(self):
        return self.experiment_id
