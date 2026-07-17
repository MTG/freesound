from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings

from user_feedback.experiments import CategoryValidation, Experiment


class _ToyExperiment(Experiment):
    """Test-only experiment: exercises the generic base seam in isolation, with no
    dependency on real models/context. Proves the machinery is reusable. Not shipped."""

    experiment_id = "toy"


class _FakeSound:
    """Duck-typed stand-in: is_context_eligible only reads .bst_category, so a real Sound is not needed here."""

    def __init__(self, bst_category):
        self.bst_category = bst_category


@override_settings(FEEDBACK_SAMPLE_RATES={"toy": 1.0})
class ExperimentBaseTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            "alice", email="alice@freesound.org", password="testpass"
        )

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_anonymous_never_shown(self):
        self.assertFalse(_ToyExperiment().should_show(self._request(AnonymousUser())))

    @override_settings(FEEDBACK_SAMPLE_RATES={"toy": 0.0})
    def test_rate_zero_never_sampled(self):
        self.assertFalse(_ToyExperiment().is_sampled_in(self._request(self.user)))

    def test_rate_one_always_sampled(self):
        self.assertTrue(_ToyExperiment().is_sampled_in(self._request(self.user)))

    @override_settings(FEEDBACK_SAMPLE_RATES={"toy": 0.5})
    def test_sampling_is_deterministic(self):
        experiment = _ToyExperiment()
        request = self._request(self.user)
        # Same user -> same verdict every time (no re-rolling per page load).
        self.assertEqual(experiment.is_sampled_in(request), experiment.is_sampled_in(request))

    def test_throttled_after_answering(self):
        experiment = _ToyExperiment()
        request = self._request(self.user)
        self.assertTrue(experiment.should_show(request))          # shown before answering
        experiment.save_response(self.user, {"answer": "yes"})    # yes/no only
        self.assertFalse(experiment.should_show(request))         # not shown again after

    def test_category_validation_needs_a_category(self):
        experiment = CategoryValidation()
        request = self._request(self.user)
        self.assertFalse(experiment.is_context_eligible(request, sound=None))
        self.assertFalse(experiment.is_context_eligible(request, sound=_FakeSound("")))
        self.assertTrue(experiment.is_context_eligible(request, sound=_FakeSound("music")))
