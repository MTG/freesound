from django.conf import settings
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
