from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from user_feedback.experiments import CategoryValidation, Experiment
from user_feedback.models import UserFeedback
from utils.test_helpers import create_user_and_sounds


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


class SubmitAndModalViewTest(TestCase):
    """The generic submit + modal views, driven through their real URLs with the
    test client -- i.e. exactly what the box and modal hit in the browser."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, sounds = create_user_and_sounds(bst_category="fx-o")
        self.sound = sounds[0]
        self.client.force_login(self.user)
        self.submit_url = reverse("user-feedback-submit")
        self.modal_url = reverse("user-feedback-modal")

    def _rows(self):
        return UserFeedback.objects.filter(experiment_id="category_validation")

    def _submit(self, ajax=False, **data):
        data.setdefault("experiment_id", "category_validation")
        data.setdefault("sound_id", self.sound.id)
        return self.client.post(self.submit_url + ("?ajax=1" if ajax else ""), data)

    # -- submit: saved answers --
    def test_yes_saves_row_and_redirects(self):
        response = self._submit(answer="yes")
        self.assertEqual(response.status_code, 302)
        row = self._rows().get()
        self.assertEqual(row.user, self.user)
        # cleaned_data of the whole form is stored; the two extras are empty for "yes".
        self.assertEqual(
            row.data, {"answer": "yes", "sound_id": self.sound.id, "selected_category": "", "text": ""}
        )

    def test_yes_ajax_returns_json(self):
        response = self._submit(ajax=True, answer="yes")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["content-type"])
        self.assertEqual(self._rows().count(), 1)

    def test_no_with_category_saves(self):
        response = self._submit(ajax=True, answer="no", selected_category="ss-n", text="wrong one")
        self.assertIn("application/json", response["content-type"])
        row = self._rows().get()
        self.assertEqual(row.data["answer"], "no")
        self.assertEqual(row.data["selected_category"], "ss-n")
        self.assertEqual(row.data["text"], "wrong one")

    # -- submit: client ip --
    @override_settings(DEBUG=False)
    def test_submit_stores_forwarded_ip(self):
        self.client.post(
            self.submit_url,
            {"experiment_id": "category_validation", "sound_id": self.sound.id, "answer": "yes"},
            HTTP_X_FORWARDED_FOR="5.6.7.8",
        )
        self.assertEqual(self._rows().get().ip, "5.6.7.8")

    @override_settings(DEBUG=False)
    def test_submit_without_proxy_header_stores_no_ip(self):
        # get_client_ip returns "-" with no header; the view stores NULL, not "-"
        # (which the ip column would reject).
        self.client.post(
            self.submit_url,
            {"experiment_id": "category_validation", "sound_id": self.sound.id, "answer": "yes"},
        )
        self.assertIsNone(self._rows().get().ip)

    # -- submit: rejected, nothing saved --
    def test_no_without_category_is_rejected(self):
        response = self._submit(ajax=True, answer="no")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("application/json", response["content-type"])  # re-rendered form HTML
        self.assertEqual(self._rows().count(), 0)

    def test_tampered_sound_id_is_rejected(self):
        response = self._submit(ajax=True, answer="yes", sound_id=999999999)
        self.assertNotIn("application/json", response["content-type"])
        self.assertEqual(self._rows().count(), 0)

    def test_unknown_experiment_returns_404(self):
        self.assertEqual(self._submit(experiment_id="does-not-exist", answer="yes").status_code, 404)

    # -- submit: method / auth guards --
    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.submit_url).status_code, 405)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self._submit(answer="yes")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.assertEqual(self._rows().count(), 0)

    # -- modal view --
    def _modal(self, answer):
        return self.client.get(
            self.modal_url,
            {"experiment_id": "category_validation", "sound_id": self.sound.id, "answer": answer, "ajax": "1"},
        )

    def test_modal_no_variant_has_category_field(self):
        self.assertContains(self._modal("no"), 'name="selected_category"')

    def test_modal_yes_variant_has_no_category_field(self):
        self.assertNotContains(self._modal("yes"), 'name="selected_category"')

    def test_modal_unknown_experiment_404(self):
        self.assertEqual(self.client.get(self.modal_url, {"experiment_id": "nope"}).status_code, 404)


@override_settings(FEEDBACK_SAMPLE_RATES={"category_validation": 1.0})
class PerSoundThrottleTest(TestCase):
    """Answering about one sound must not stop the box appearing on other sounds:
    category_validation throttles per sound, not once per user like the base class."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, self.sounds = create_user_and_sounds(num_sounds=2, bst_category="fx-o")
        self.experiment = CategoryValidation()

    def _request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return request

    def test_answering_one_sound_does_not_throttle_another(self):
        first, second = self.sounds
        request = self._request()
        self.assertTrue(self.experiment.should_show(request, sound=first))
        self.assertTrue(self.experiment.should_show(request, sound=second))

        self.experiment.save_response(self.user, {"answer": "yes", "sound_id": first.id})

        self.assertFalse(self.experiment.should_show(request, sound=first))   # answered -> hidden
        self.assertTrue(self.experiment.should_show(request, sound=second))   # untouched -> still shown


@override_settings(FEEDBACK_SAMPLE_RATES={"category_validation": 0.5})
class PerUserSoundSamplingTest(TestCase):
    """category_validation samples per (user, sound): every user can be asked and the
    rate gates each sound they open, rather than a fixed cohort of users."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, self.sounds = create_user_and_sounds(num_sounds=2, bst_category="fx-o")
        self.experiment = CategoryValidation()

    def _request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return request

    def test_key_depends_on_both_user_and_sound(self):
        request = self._request()
        first, second = self.sounds
        key_first = self.experiment.sampling_key(request, sound=first)
        self.assertIn(str(self.user.id), key_first)
        self.assertIn(str(first.id), key_first)
        # same user, different sound -> different key (so the rate is rolled per sound)
        self.assertNotEqual(key_first, self.experiment.sampling_key(request, sound=second))

    def test_verdict_is_stable_for_same_user_and_sound(self):
        request = self._request()
        sound = self.sounds[0]
        # deterministic: same (user, sound) lands the same way on every page load
        self.assertEqual(
            self.experiment.is_sampled_in(request, sound=sound),
            self.experiment.is_sampled_in(request, sound=sound),
        )
